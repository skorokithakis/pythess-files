# Copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A super simple OpenFlow learning switch that installs rules for
each pair of L2 addresses.
"""

# These next two imports are common POX convention
from collections import Counter, defaultdict
import networkx as nx
import time
import threading
from pox.core import core
import pox.openflow.discovery
import pox.host_tracker
import pox.openflow.spanning_tree as spanning_tree
import pox.openflow.libopenflow_01 as of
import pox.lib.util as poxutil  # handle args on initial launch
from pox.lib.recoco import Timer
from pox.openflow.of_json import *
log = core.getLogger()


class SimpleController(object):
    """
    This is the controller class. Register on launch
    """
    def __init__(self):
        self.switch_links_to_port = {}
        self.paths_applied = {}
        self.spanning_tree = {}  # the spanning tree in case we have loops
        self.mac_to_port = {}
        self.topology = nx.Graph()
        self.loop = []

        # This table maps (switch,MAC-addr) pairs to the port on 'switch' at
        # which we last saw a packet *from* 'MAC-addr'.
        # (In this case, we use a Connection object for the switch.)
        self.table = {}

        self.ip_to_mac = {}
        self.traffic_pair_counter = Counter()
        # To send out all ports, we can use either of the special ports
        # OFPP_FLOOD or OFPP_ALL.  We'd like to just use OFPP_FLOOD,
        # but it's not clear if all switches support this, so we make
        # it selectable.
        self.all_ports = of.OFPP_FLOOD

        # bandwidth variables START--------------------------------------------------------->
        self.switches_bw = defaultdict(lambda: defaultdict(int))  # holds switches ports last seen bytes
        # bandwidth variables END----------------------------------------------------------->

        # get stats START ------------------------------------------------------------------>
        # core.openflow.addListenerByName("FlowStatsReceived", self._handle_flowstats_received)
        core.openflow.addListenerByName("PortStatsReceived", self._handle_portstats_received)
        core.openflow.addListenerByName("QueueStatsReceived", self._handle_qeuestats_received)
        # get stats END -------------------------------------------------------------------->
        core.openflow.addListenerByName("PacketIn", self._handle_PacketIn)
        core.openflow.addListenerByName("ConnectionUp", self._handle_ConnectionUp)
        core.openflow_discovery.addListenerByName("LinkEvent", self._handle_LinkEvent)  # listen to openflow_discovery
        core.host_tracker.addListenerByName("HostEvent", self._handle_HostEvent)  # listen to host_tracker

    def _handle_qeuestats_received (self, event):
        """
        handler to manage queued packets statistics received
        Args:
            event: Event listening to QueueStatsReceived from openflow
        """
        stats = flow_stats_to_list(event.stats)
        # log.info("QueueStatsReceived from %s: %s", dpidToStr(event.connection.dpid), stats)

    def _handle_portstats_received(self,event):
        """
        Handler to manage port statistics received
        Args:
            event: Event listening to PortStatsReceived from openflow
        """
        for f in event.stats:
            if int(f.port_no)<65534: # used from hosts and switches interlinks
                current_bytes = f.rx_bytes + f.tx_bytes  # transmitted and received
                try:
                    last_bytes = self.switches_bw[int(event.connection.dpid)][int(f.port_no)]
                except:
                    last_bytes = 0
                estim_bw = (((current_bytes - last_bytes)/1024)/1024)*8
                estim_bw = float(format(estim_bw, '.2f'))
                if estim_bw > 0:
                    print pox.lib.util.dpidToStr(event.connection.dpid), f.port_no, estim_bw

                self.switches_bw[int(event.connection.dpid)][int(f.port_no)] = (f.rx_bytes + f.tx_bytes)

    def _timer_func (self):
        """
        Recurring function to request stats from switches
        for each connection (which represents a switch actually)
        request statistics
        """
        for connection in core.openflow._connections.values():
            # connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))

            connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
            connection.send(of.ofp_stats_request(body=of.ofp_queue_stats_request()))
        # log.info("Sent %i flow/port stats request(s)", len(core.openflow._connections))

    def _handle_ConnectionUp(self, event):
        """
        Fired up openflow connection with the switch
        Args:
            event:

        Returns:

        """
        self.topology.add_node(pox.lib.util.dpid_to_str(event.dpid))
        Timer(1, self._timer_func, recurring=True)
        # print self.topology.nodes()
        self.switches_bw[int(event.dpid)] = {}

    def _handle_LinkEvent(self, event):
        """
        Listen to link events between our network components. Specifically
        interested in links between switches at the moment. Each time such
        event occurs we pass arguments in a threaded function to run async
        Args:
            event: LinkEvent listening to openflow.discovery
        Returns: Nothing at the moment, saves topology graph and spanning tree
        """
        s1 = pox.lib.util.dpid_to_str(event.link.dpid1)  # the first switch in the link event
        s2 = pox.lib.util.dpid_to_str(event.link.dpid2)  # the second switch in the link event
        p1, p2 = event.link.port1, event.link.port2  # the port fo the first switch
        self.switch_links_to_port[s1, s2] = (p1, p2)
        print self.switch_links_to_port
        ltrt = threading.Thread(target=self.link_event_to_topology, args=(s1, s2))
        ltrt.start()

    def link_event_to_topology(self, s1, s2):
        """
        Add switches to networkx topology graph and check for loops
        if our topology contains loops we calculate the spanning tree
        to be used for the first packets when destination will be unknown
        Args:
            s1: first switch in the link ex. "00-00-00-00-00-01"
            s2: second switch in the link ex. "00-00-00-00-00-02"
        Returns: nada
        """
        self.topology.add_edge(s1, s2, weight=100)  # the port of the second switch
        try:
            self.loop = nx.cycle_basis(self.topology)[0]
            self.spanning_tree = spanning_tree._calc_spanning_tree()
        except:
            self.loop = []

    def _handle_HostEvent(self, event):
        """
        Listen to host_tracker events, fired up every time a host is up or down
        When this happens we need the topology. For now must issue a pingall from
        mininet cli. Later to fire own pings?
        To handle topology a thread is launched with arguments the host and the switch
        Args:
            event: HostEvent listening to core.host_tracker
        Returns: nada
        """
        macaddr = event.entry.macaddr.toStr()
        s = pox.lib.util.dpid_to_str(event.entry.dpid)
        self.mac_to_port[macaddr] = event.entry.port
        # time.sleep(5)
        htrt = threading.Thread(target=self.add_host_to_topology, args=(s, macaddr))
        htrt.start()

    def add_host_to_topology(self, s, macaddr):
        """
        Handle graph related methods with async Timer
        Args:
            s: the switch
            macaddr: the host
        Returns: nada
        """
        # time.sleep(5)
        self.topology.add_node(macaddr)
        self.topology.add_edge(s, macaddr, weight=10)
        # print self.topology.edges(data=True)
        # print self.topology.nodes(data=True)

    def _handle_PacketIn (self, event):
        """
        Handle messages the switch has sent us because it has no
        matching rule.
        Args:
            event: event parsed from PacketIn
        Returns: nada
        """
        packet = event.parsed

        # Learn the source
        self.table[(event.connection,packet.src)] = event.port
        if packet.type == packet.IPV6_TYPE:
            msg = of.ofp_packet_out()
            msg.buffer_id = None
            msg.in_port = event.port
            event.connection.send(msg)
            return

        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return
        if packet.type == 2048:
            pkt = packet.find('ipv4')
            self.ip_to_mac[pkt.srcip.toStr()] = packet.src
            self.ip_to_mac[pkt.dstip.toStr()] = packet.dst
            self.traffic_pair_counter[packet.src, packet.dst] += 1
        dst_port = self.table.get((event.connection, packet.dst))

        if len(self.loop) > 0:
            self.calculate_shortest_path(str(packet.src), str(packet.dst))

            # we have a loop caution
            if dst_port is None:
                # We don't know where the destination is yet.  So, we'll just
                # send the packet out all ports in the spanning tree
                # and hope the destination is out there somewhere. :)
                msg = of.ofp_packet_out(data=event.ofp)

                tree_ports = [p[1] for p in self.spanning_tree.get(event.dpid, [])]
                # print tree_ports
                for p in event.connection.ports:
                    if p >= of.OFPP_MAX:
                        # Not a normal port
                        continue

                    if not core.openflow_discovery.is_edge_port(event.dpid, p):
                        # If the port isn't a switch-to-switch port, it's fine to flood
                        # through it.  But if it IS a switch-to-switch port, we only
                        # want to use it if it's on the spanning tree.
                        if p not in tree_ports:
                            continue

                    msg.actions.append(of.ofp_action_output(port=p))

                event.connection.send(msg)
            else:
                # Since we know the switch ports for both the source and dest
                # MACs, we can install rules for both directions.
                msg = of.ofp_flow_mod()
                msg.match.dl_dst = packet.src
                msg.match.dl_src = packet.dst
                msg.priority = 1
                msg.hard_timeout = int(self.traffic_pair_counter[packet.dst, packet.src] * 2)
                msg.idle_timeout = int(self.traffic_pair_counter[packet.dst, packet.src])
                msg.actions.append(of.ofp_action_output(port=event.port))
                event.connection.send(msg)

                # This is the packet that just came in -- we want to
                # install the rule and also resend the packet.
                msg = of.ofp_flow_mod()
                msg.data = event.ofp  # Forward the incoming packet
                msg.match.dl_src = packet.src
                msg.match.dl_dst = packet.dst
                msg.priority = 1
                msg.hard_timeout = int(self.traffic_pair_counter[packet.src, packet.dst] * 2)
                msg.idle_timeout = int(self.traffic_pair_counter[packet.src, packet.dst])
                msg.actions.append(of.ofp_action_output(port=dst_port))
                event.connection.send(msg)

                # log.info("Installing %s <-> %s" % (packet.src, packet.dst))
        else:
            # no loop detected, process packet as usual
            if dst_port is None:
                # We don't know where the destination is yet.  So, we'll just
                # send the packet out all ports (except the one it came in on!)
                # and hope the destination is out there somewhere. :)
                msg = of.ofp_packet_out(data=event.ofp)
                msg.actions.append(of.ofp_action_output(port=self.all_ports))
                event.connection.send(msg)
            else:
                # Since we know the switch ports for both the source and dest
                # MACs, we can install rules for both directions.
                msg = of.ofp_flow_mod()
                msg.match.dl_dst = packet.src
                msg.match.dl_src = packet.dst
                msg.priority = 1
                msg.hard_timeout = int(self.traffic_pair_counter[packet.dst, packet.src] * 2)
                msg.idle_timeout = int(self.traffic_pair_counter[packet.dst, packet.src])
                msg.actions.append(of.ofp_action_output(port=event.port))
                event.connection.send(msg)

                # This is the packet that just came in -- we want to
                # install the rule and also resend the packet.
                msg = of.ofp_flow_mod()
                msg.data = event.ofp  # Forward the incoming packet
                msg.match.dl_src = packet.src
                msg.match.dl_dst = packet.dst
                msg.priority = 1
                msg.hard_timeout = int(self.traffic_pair_counter[packet.src, packet.dst] * 2)
                msg.idle_timeout = int(self.traffic_pair_counter[packet.src, packet.dst])
                msg.actions.append(of.ofp_action_output(port=dst_port))
                event.connection.send(msg)

                # log.info("Installing %s <-> %s" % (packet.src, packet.dst))

    def calculate_shortest_path(self, source_mac, dst_mac):
        """
        If we have a source and a target mac address we try to calculate a shortest path
        for this flow from our topology in networkx. If there is a shortest path
        we fire up the shortest_path_flow_modifications where we  analyse the path and
        create and install the flows on the switches
        Args:
            source_mac: the source of the request
            dst_mac: the destination of the request
        """
        if source_mac in self.topology.nodes() and dst_mac in self.topology.nodes():
            shortest_path = nx.shortest_path(self.topology, source=source_mac, target=dst_mac)
            print shortest_path
            print len(shortest_path)
            if len(shortest_path)>2:
                self.shortest_path_flow_modifications(shortest_path)

    def shortest_path_flow_modifications(self, shortest_path):
        """
        Analyze a shortest path to datapaths and apply flow modification
        rules
        Args:
            shortest_path: the shortest path calculated in calculate_shortest_path
        """
        source = shortest_path[0]
        target = shortest_path[-1]
        if not self.paths_applied.get((source,target)):
            sourceip = self.ip_to_mac.get(source)
            targetip = self.ip_to_mac.get(target)
            switch_only = shortest_path[1:-1]
            for con in core.openflow._connections.values():

                if pox.lib.util.dpid_to_str(con.dpid) in switch_only:
                    switch_index = shortest_path.index(pox.lib.util.dpid_to_str(con.dpid))
                    ip_port_prev_datapath = shortest_path[switch_index-1]
                    ip_port_next_datapath = shortest_path[switch_index+1]
                    if ":" in ip_port_prev_datapath and ":" in ip_port_next_datapath:
                        in_port = self.mac_to_port.get(ip_port_prev_datapath)
                        out_port = self.mac_to_port.get(ip_port_next_datapath)
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if ":" in ip_port_prev_datapath and "-" in ip_port_next_datapath:
                        print pox.lib.util.dpid_to_str(con.dpid), ip_port_next_datapath
                        in_port = self.mac_to_port.get(ip_port_prev_datapath)
                        out_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid),ip_port_next_datapath))[0]
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if ":" in ip_port_next_datapath and "-" in ip_port_prev_datapath:
                        in_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid),ip_port_prev_datapath))[1]
                        out_port = self.mac_to_port.get(ip_port_next_datapath)
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if "-" in ip_port_next_datapath and "-" in ip_port_prev_datapath:
                        # switch -- switch -- switch
                        in_port = self.switch_links_to_port.get((ip_port_prev_datapath, pox.lib.util.dpid_to_str(con.dpid)))[1]
                        out_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid), ip_port_next_datapath))[0]
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    self.paths_applied[(source,target)] = shortest_path
        #reversed
        shortest_path.reverse()
        source = shortest_path[0]
        target = shortest_path[-1]
        if not self.paths_applied.get((source,target)):
            sourceip = self.ip_to_mac.get(source)
            targetip = self.ip_to_mac.get(target)
            switch_only = shortest_path[1:-1]
            for con in core.openflow._connections.values():
                if pox.lib.util.dpid_to_str(con.dpid) in switch_only:
                    switch_index = shortest_path.index(pox.lib.util.dpid_to_str(con.dpid))
                    ip_port_prev_datapath = shortest_path[switch_index-1]
                    ip_port_next_datapath = shortest_path[switch_index+1]
                    if ":" in ip_port_prev_datapath and ":" in ip_port_next_datapath:
                        in_port = self.mac_to_port.get(ip_port_prev_datapath)
                        out_port = self.mac_to_port.get(ip_port_next_datapath)
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if ":" in ip_port_prev_datapath and "-" in ip_port_next_datapath:
                        print pox.lib.util.dpid_to_str(con.dpid), ip_port_next_datapath
                        in_port = self.mac_to_port.get(ip_port_prev_datapath)
                        out_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid),ip_port_next_datapath))[0]
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if ":" in ip_port_next_datapath and "-" in ip_port_prev_datapath:
                        in_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid),ip_port_prev_datapath))[1]
                        out_port = self.mac_to_port.get(ip_port_next_datapath)
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    if "-" in ip_port_next_datapath and "-" in ip_port_prev_datapath:
                        # switch -- switch -- switch
                        in_port = self.switch_links_to_port.get((ip_port_prev_datapath, pox.lib.util.dpid_to_str(con.dpid)))[1]
                        out_port = self.switch_links_to_port.get((pox.lib.util.dpid_to_str(con.dpid), ip_port_next_datapath))[0]
                        msg = of.ofp_flow_mod()
                        msg.match = of.ofp_match()
                        msg.match._in_port = in_port
                        msg.match.dl_src = EthAddr(source)
                        msg.match.dl_dst = EthAddr(target)
                        msg.priority = 100
                        msg.actions.append(of.ofp_action_output(port = out_port))
                        con.send(msg)
                    self.paths_applied[(source,target)] = shortest_path

# @poxutil.eval_args
def launch ():
    """
    Launch for the main SDN Controller Application Component
    Launch with sudo python pox.py pythess. On launch we fire up
    discovery to discover openflow enabled switches
    and host_tracker to discover hosts connected on our switches
    """
    pox.openflow.discovery.launch()
    pox.host_tracker.launch()
    sdnc = SimpleController()
    core.register(sdnc)

    log.info("PyThess SDN Demo Controller Running.")
