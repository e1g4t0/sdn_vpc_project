from ryu.app.wsgi import ControllerBase, route, WSGIApplication
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet, ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet.ethernet import ethernet
from ryu.ofproto import ofproto_v1_0
from webob.response import Response

peering = dict()

def is_allowed(src, dest):

    if src == dest:
        return True

    if src not in peering:
        return False

    allowed_vpcs_src = peering.get(src)
    allowed_vpcs_dest = peering.get(dest)

    return (src in allowed_vpcs_dest) or (dest in allowed_vpcs_src)


class VPC_IMPL(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    _CONTEXTS = {'wsgi' : WSGIApplication}


    def __init__(self, *args, **kwargs):
        super(VPC_IMPL, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(RestController, {"VPC" : self})


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data

        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt:
                src = ip_pkt.src
                dest = ip_pkt.dst

                vpc_num_src = src.split('.')[2]
                vpc_num_dest = dest.split('.')[2]

                if not is_allowed(vpc_num_src, vpc_num_dest):
                    return

        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        dp.send_msg(out)

class RestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.VPC = data['VPC']

    @route('update_peering', '/peering/{vpc1}/{vpc2}', methods=['POST'])
    def enable(self, req, vpc1, vpc2, **kwargs):

        set_vpc1 = set()
        set_vpc2 = set()

        if vpc1 in peering:
            set_vpc1 = peering[vpc1]

        if vpc2 in peering:
            set_vpc2 = peering[vpc2]

        set_vpc1.add(vpc2)
        set_vpc2.add(vpc1)

        peering[vpc1] = set_vpc1
        peering[vpc2] = set_vpc2

        return Response('The peering between vpc {0} and vpc {1} has been enabled\n'.format(vpc1, vpc2))

    @route('delete_peering', '/peering/{vpc1}/{vpc2}', methods=['DELETE'])
    def delete(self, req, vpc1, vpc2, **kwargs):

        if vpc1 in peering and vpc2 in peering[vpc1]:
            peering[vpc1].remove(vpc2)

        if vpc2 in peering and vpc1 in peering[vpc2]:
            peering[vpc2].remove(vpc1)

        return Response('The peering between vpc {0} and vpc {1} has been disabled\n'.format(vpc1, vpc2))