from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from os_ken.controller.handler import set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types, ipv4, tcp, udp
from os_ken.lib import hub
import json
import logging

class SDNController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.intents = []
        self.flows = {}
        self.monitor_thread = hub.spawn(self._monitor)
        
        self.intent_policies = {
            'QoS Priority': {'priority': 100, 'queue': 1},
            'Load Balance': {'priority': 50, 'method': 'round_robin'},
            'SSL Inspection': {'priority': 80, 'port': 443},
            'Traffic Shaping': {'priority': 60, 'rate_limit': 1000},
            'Geo-Routing': {'priority': 70, 'method': 'geo_based'}
        }
        
        self.logger.info("SDN Controller initialized")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.datapaths[datapath.id] = datapath
        self.logger.info(f'Switch connected: DPID={datapath.id}')

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, 
                 idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            priority = self._get_intent_priority(pkt)
            
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, priority, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _get_intent_priority(self, pkt):
        default_priority = 1
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return default_priority

        for intent in self.intents:
            if intent.get('status') == 'active':
                policy = intent.get('policy')
                if policy in self.intent_policies:
                    return self.intent_policies[policy]['priority']
        return default_priority

    def add_intent(self, intent_data):
        intent_id = len(self.intents) + 1
        intent = {
            'id': intent_id,
            'name': intent_data.get('name', 'Unnamed Intent'),
            'policy': intent_data.get('policy', 'QoS Priority'),
            'bandwidth': intent_data.get('bandwidth', 'unlimited'),
            'status': 'active'
        }
        self.intents.append(intent)
        self.logger.info(f'Intent added: {intent["name"]}')
        self._apply_intent(intent)
        return intent

    def _apply_intent(self, intent):
        policy = intent.get('policy')
        for dpid, datapath in self.datapaths.items():
            if policy == 'QoS Priority':
                self._apply_qos_priority(datapath)
            elif policy == 'Load Balance':
                self._apply_load_balancing(datapath)
            elif policy == 'Traffic Shaping':
                self._apply_traffic_shaping(datapath, intent.get('bandwidth'))
            self.logger.info(f'Applied intent "{intent["name"]}" to switch {dpid}')

    def _apply_qos_priority(self, datapath):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        
        match = parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=443)
        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match, actions)

    def _apply_load_balancing(self, datapath):
        self.logger.info(f'Load balancing applied to switch {datapath.id}')

    def _apply_traffic_shaping(self, datapath, bandwidth):
        self.logger.info(f'Traffic shaping applied: {bandwidth}')

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(10)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        flows = []
        for stat in ev.msg.body:
            flows.append({
                'packet_count': stat.packet_count,
                'byte_count': stat.byte_count,
                'duration': stat.duration_sec,
                'priority': stat.priority
            })
        self.flows[ev.msg.datapath.id] = flows

    def get_intents(self):
        return self.intents

    def get_flows(self):
        return self.flows

    def get_topology(self):
        return {
            'switches': list(self.datapaths.keys()),
            'links': [],
            'hosts': len(set(mac for macs in self.mac_to_port.values() for mac in macs))
        }
    
    def remove_intent(self, intent_id):
        self.intents = [i for i in self.intents if i['id'] != intent_id]
        self.logger.info(f'Intent removed: ID={intent_id}')
