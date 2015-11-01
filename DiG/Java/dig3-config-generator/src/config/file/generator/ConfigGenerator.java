/* ***** BEGIN LICENSE BLOCK *****
 * DiG: Data centers in the Grid
 * Copyright (C) 2015-2016, INRIA.
 * 
 * This work was partially supported by the ANR Reflexion Project (ANR-14-CE28-0019).
 * The authors alone are responsible for this work.
 *
 * See the file AUTHORS for details and contact information.
 * 
 * This file is part of DiG (Data centers in the Grid Tool).
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License Version 3 or later
 * (the "GPL"), or the GNU Lesser General Public License Version 3 or later
 * (the "LGPL") as published by the Free Software Foundation.
 *
 * DiG is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * or the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License and
 * GNU Lesser General Public License along with DiG; see the file
 * COPYING. If not, see <http://www.gnu.org/licenses/>.
 *
 * ***** END LICENSE BLOCK ***** */
//Author: Hardik Soni <hardik.soni@inria.fr>

/**
 * 
 */
package config.file.generator;
import java.io.BufferedWriter;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import org.cesta.parsers.dot.DotTree;


public class ConfigGenerator {

	private static final String OFPort = "6633";
	private static String managerIP;
	
	private static final String HadoopPropertyID = "hadoop";
	private static final String CPUNodePropertyID = "cpu";
	private static final String IPNodePropertyID = "ip";
	private static final String TypeNodePropertyID = "type";
	private static final String BWLinkPropertyID = "bandwidth";
	private static final String StorageNodePropertyID = "storage";
	private static final String containerNodePropertyID = "container";

	private static int virtualNodeIPSubnetMask = 16;
	private static final String virtNetIntfMacPrefix = "fe";
	private static int virtNetIntfMacIndex = 1;
	private static final String NameNodeIP = "10.0.10.1" +"/"+ Integer.toString(virtualNodeIPSubnetMask);
	private static final String ResourceManagerIP = "10.0.10.2"+"/"+ Integer.toString(virtualNodeIPSubnetMask);
	private static final String virtualHostMacPrefix = "52:54:00";

	
	private static int slaveIPIndex = 167772160; //10.0.0.0
	
	private static int virtualHostMacIndex = 1;
	private static int virtualHostSlaveIndex = 0;

	private static long dpid;
	
	private DotTree.Graph physicalNet;
	private DotTree.Graph virtualNet;
	private HashMap<String, ArrayList<String>> nodeMapping;
	
	private HashMap<String, String> vToPMap;
	private HashMap<String, PhysicalNodeContext> contextMap;
	private PhysicalNodeContext managerNodeContext;
	
	ConfigGenerator(DotTree.Graph physicalGraph, DotTree.Graph virtualGraph, 
			HashMap<String, ArrayList<String>> mapping) {

		physicalNet = physicalGraph;
		virtualNet = virtualGraph;
		vToPMap = new HashMap <String, String>();
		contextMap = new HashMap<String, PhysicalNodeContext>();
		dpid = 0;
		nodeMapping = mapping;
	}
	
	private String findIPPropOfNodeFromGraph (String nodeId, DotTree.Graph graphObj)  {
		String ip = null;
		DotTree.Node node = graphObj.nodes.get(nodeId);
		if (node != null) {
			ip = node.attributes.get(IPNodePropertyID);
		}
		return ip;
	}
	
	private String findCPUPropOfNodeFromGraph (String nodeId, DotTree.Graph graphObj)  {
		String cpu = null;
		DotTree.Node node = graphObj.nodes.get(nodeId);
		if (node != null) {
			cpu = node.attributes.get(CPUNodePropertyID);
		}
		return cpu;
	}
	
	private String findPropOfNodeFromGraph(String propId, String nodeId, DotTree.Graph graphObj) {
		String value = null;
		DotTree.Node node = graphObj.nodes.get(nodeId);
		if (node != null) {
			value = node.attributes.get(propId);
		}
		return value;
	}
	
	private static String getNextDPId() {
		String dpidStr = Long.toHexString(++dpid);
		int l = dpidStr.length();
		for (int i=0; i<16-l; i++)
			dpidStr = "0" + dpidStr;
		return dpidStr;
	}
	
	private static String getNextVirtualHostMac() {
		return getNextVirtualMac(virtualHostMacPrefix, virtualHostMacIndex++);
	}
	
	private static String getNextVirtualMac(String prefix, int index) {
		String macStr = new String(prefix);
		String mac = Long.toHexString(index);
		int l = mac.length();
		for (int i=0; i<6-l; i++)
			mac = "0" + mac;
		for (int i =0; i<3; i++) {
			macStr +=  ":" + mac.substring(2*i, 2*(i+1));	
		}
		return macStr;
	}
	
	private static String getMac (String prefix, int index) {
		String macStr = new String(prefix);
		String mac = Long.toHexString(index);
		int l = mac.length();
		for (int i=0; i<10-l; i++)
			mac = "0" + mac;
		for (int i =0; i<5; i++) {
			macStr +=  ":" + mac.substring(2*i, 2*(i+1));	
		}
		return macStr;
	}
	
	private static String getNextVirtualSwitchIntfMac() {
		return getMac (virtNetIntfMacPrefix, virtNetIntfMacIndex++);
	}
	
	
	private static String getNextSlaveIP() {
		int ip = ++slaveIPIndex;
		String ipStr = convertIPIntToString(ip);
		return ipStr + "/"+ Integer.toString(virtualNodeIPSubnetMask);
	}
	
	private static String convertIPIntToString(int ip) {
		return (String.format("%d.%d.%d.%d", 
				(ip >> 24 & 0xff),
				(ip >> 16 & 0xff),
				(ip >> 8 & 0xff),
				(ip & 0xff)
				 ));
	}
	
	private static int convertIPStringToInt(String ip) {
		int ipInt = 0;
		String[] ipParts = ip.split("\\.");
		for (int i = 0; i<4; i++) {
			ipInt = (Integer.parseInt(ipParts[i]) << ((3-i)*8)) | ipInt;
		}
		return ipInt;
	}
	
	private static String getSubnetAddressFromIP(String ip4) {
		String[] classlessIP = ip4.split("/");
		int prefix = Integer.parseInt(classlessIP[1]);
		int ip = convertIPStringToInt(classlessIP[0]);
		int mask = 0xffffffff << (32-prefix);
		int subnet = ip & mask;
		return (convertIPIntToString(subnet)  + "/"+classlessIP[1]);
	}
	
	private static String getBroadcastIPFromIPandNetMask (String ip) {
		String[] classlessIP = ip.split("/");
		int ipInt = convertIPStringToInt(classlessIP[0]);
		int m = 0xffffffff << (32-Integer.parseInt(classlessIP[1]));
		int bip = ipInt | ~m;
		return convertIPIntToString(bip);
	}
	private static String getNextSlaveHostName() {
		virtualHostSlaveIndex++;
		String hostName = "slave" + (Integer.toString(virtualHostSlaveIndex));
		return hostName;
	}
	
	private boolean checkInputGraphsAndMapping() {
		
		//loose sanity test on valid mapping.
		//one virtual node on one physical node
		for(Map.Entry<String, ArrayList<String>> entry : nodeMapping.entrySet()) {
			for(String str : entry.getValue()) {
				if (!vToPMap.containsKey(str))
					vToPMap.put(str, entry.getKey());
				else {
					System.out.println("error in mapping");
					return false;
				}
			}
		}
		
		for(String pnId : nodeMapping.keySet() ){
			if (findIPPropOfNodeFromGraph(pnId, physicalNet) == null) {
				System.out.println(pnId + " does not have ip property ");
				return false;
			}
		}
		
		boolean managerFlag = false;
		//check "type" property in physical network graph
		for(DotTree.Node pn : physicalNet.getNodes()) {
			if (pn.attributes.containsKey(TypeNodePropertyID)) {
				String val = pn.attributes.get(TypeNodePropertyID);
				if (val.compareTo("manager") == 0) {
					managerIP = pn.attributes.get(IPNodePropertyID);
					managerFlag = true;
				}
			}
		}
		if (!managerFlag) {
			System.out.println("Deployment Manager does not exist in physical network");
			return false;
		}
		
		//check "type" property in virtual network graph
			for(DotTree.Node vn : virtualNet.getNodes()) {
			if (vn.attributes.containsKey(TypeNodePropertyID)) {
				String val = vn.attributes.get(TypeNodePropertyID);
				if (val.compareTo("switch") != 0 && val.compareTo("host") != 0) {
					System.out.println("unknown type property value for "+vn.id);
					return false;
				}
			}
			else {
				System.out.println(vn.id + " does not have type property ");
				return false;
			}
		}

		//check "container" property in virtual network graph
//		for(DotTree.Node vn : virtualNet.getNodes()) {
//			if (vn.attributes.containsKey(containerNodePropertyID)) {
//				String val = vn.attributes.get(TypeNodePropertyID);
//				String contVals[] = val.split(",");
//				if (contVals.length != 2) {
//					System.out.println("comma seperated 2 ints for container property at virtual node "+vn.id);
//					return false;
//				}
//			}
//			else {
//				System.out.println(vn.id + " does not have type property " + containerNodePropertyID);
//				return false;
//			}
//		}

		//check bandwidth prop on virtual topo
		for(DotTree.NodePair vnp : virtualNet.getNodePairs()) {
			if (vnp.attributes.containsKey(BWLinkPropertyID)) {
				String val = vnp.attributes.get(BWLinkPropertyID);
				if (val.compareTo("") == 0 ) {
					System.out.println("bandwidth not mentioned for "+vnp.toString());
					return false;
				}
			}
			else {
				System.out.println(vnp.toString() + " does not have bandwidth property ");
				return false;
			}
		}
		return true;
	}
	
	private void createPhysicalNodeContexts() {
		
		if (!checkInputGraphsAndMapping()) {
			System.out.println("error in data");
			return;
		}

		PhysicalNodeContext nodeData = null;

//		//get manager node
//		DotTree.Node mgmtNode = null;
//		for(DotTree.Node pn : physicalNet.getNodes()) {
//			if (pn.attributes.containsKey(TypeNodePropertyID)) {
//				String val = pn.attributes.get(TypeNodePropertyID);
//				if (val.compareTo("manager") == 0) {
//					mgmtNode = pn;
//					break;
//				}
//			}
//		}
		
		//prefill hashmap entries
		for(String npid : nodeMapping.keySet()) {
			DotTree.Node pNode = physicalNet.nodes.get(npid);
			if (pNode == null) {
				System.out.println("No physical node with id "+npid+" in physical topology");
				return;
			}
			nodeData = new PhysicalNodeContext(pNode);
			contextMap.put(npid, nodeData);
		}

//		if (contextMap.get(mgmtNode.id) == null) {
//			managerNodeContext = new PhysicalNodeContext(mgmtNode);
//			contextMap.put(mgmtNode.id, managerNodeContext);
//		} else {
//			managerNodeContext = contextMap.get(mgmtNode.id);
//		}
				
		for (DotTree.NodePair vNP : virtualNet.getNodePairs()) {
			String phX = vToPMap.get(vNP.x.id);
			String phY = vToPMap.get(vNP.y.id);
			String vXNodeType;
			String vYNodeType;
			
			vXNodeType = vNP.x.attributes.get(TypeNodePropertyID);
			vYNodeType = vNP.y.attributes.get(TypeNodePropertyID);
			String virtualBWValue = vNP.attributes.get(BWLinkPropertyID);

			
			if (phX.compareTo(phY) == 0) { // both virtual node are mapped to the same node
				PhysicalNodeContext phXContext = contextMap.get(phX);
				if (vXNodeType.compareTo("switch") == 0 && vYNodeType.compareTo("switch") == 0) {
					phXContext.addAdjacentVirtualSwicthes(vNP.x, vNP.y, virtualBWValue);
				} else {
					if (vXNodeType.compareTo("switch") == 0) {
						phXContext.addAdjacentVirtualHostSwitch(vNP.y, vNP.x, virtualBWValue);
					} else {
						phXContext.addAdjacentVirtualHostSwitch(vNP.x, vNP.y, virtualBWValue);
					}
				}
			} else {
				PhysicalNodeContext phXContext = contextMap.get(phX);
				PhysicalNodeContext phYContext = contextMap.get(phY);
				
				PeerMetadata xData = phXContext.getNextMetaDataForPeer();
				PeerMetadata yData = phYContext.getNextMetaDataForPeer();

				if (vXNodeType.compareTo("switch") == 0) {
					phXContext.addVirtualSwitchInterface(vNP.x, virtualBWValue, yData);
				} else {
					phXContext.addVirtualHost(vNP.x, virtualBWValue, yData);
				}

				if (vYNodeType.compareTo("switch") == 0) {
					phYContext.addVirtualSwitchInterface(vNP.y, virtualBWValue, xData);
				}
				else {
					phYContext.addVirtualHost(vNP.y, virtualBWValue, xData);
				}
			}
		}
		
		//allocates storage to
		for(PhysicalNodeContext phNCM : contextMap.values()) {
			phNCM.allocateStorageToVirtualNodes();
			phNCM.allocateContainerToVirtualNodes();
		}
		
		//build ovs command for all the virtual switches..
		for(PhysicalNodeContext phNCM : contextMap.values()) {
			phNCM.createOVSCommandForVirtualSwithces();
			phNCM.createVHostContainerCommandForVirtualNodes();
		}
	}
	
	public void generateAllFiles (String dir ) {
		
		createPhysicalNodeContexts();

		FileOutputStream dfs;
		String dfileName = dir+"/host-clean-up.ini";
		FileOutputStream fs;
		String fileName = dir+"/host-config-exp.ini";
		try {
			PhysicalNodeContext nnpc = null;
			PhysicalNodeContext rmpc = null;
			fs = new FileOutputStream(fileName);
			BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fs));
			dfs = new FileOutputStream(dfileName);
			BufferedWriter dbw = new BufferedWriter(new OutputStreamWriter(dfs));
			
			for(PhysicalNodeContext phNCM : contextMap.values()){
				if (phNCM.containsNamenode) {
					nnpc = phNCM; continue;
				}
				if (phNCM.containsResoureManager) {
					rmpc = phNCM; continue;
				}
				String fName = phNCM.generateCommandToFile(dir);
				String dName = phNCM.generateDeleteCommandToFile(dir);
				String line  = phNCM.nodeIP + " " + fName;
				bw.write(line);
				bw.newLine();
				String dline  = phNCM.nodeIP + " " + dName;
				dbw.write(dline);
				dbw.newLine();
			}

			if (rmpc != null) {
			String fName = rmpc.generateCommandToFile(dir);
			String dName = rmpc.generateDeleteCommandToFile(dir);
			String line  = rmpc.nodeIP + " " + fName;
			bw.write(line);
			bw.newLine();
			String dline  = rmpc.nodeIP + " " + dName;
			dbw.write(dline);
			dbw.newLine();
			}
			
			if (nnpc != null) {
			String fName = nnpc.generateCommandToFile(dir);
			String dName = nnpc.generateDeleteCommandToFile(dir);
			String line  = nnpc.nodeIP + " " + fName;
			bw.write(line);
			bw.newLine();
			String dline  = nnpc.nodeIP + " " + dName;
			dbw.write(dline);
			dbw.newLine();
			}

			bw.close();
			dbw.close();
		} catch (Exception e) {
			System.out.println("Exception thrown: error in writing file named - "+fileName);
		}
	}
	
	private class VirtualNetworkInterface {
		public String vMac;
		public String vIP;
		public String bIP;
		public String virtualBw;
		public String intfName;;
		VirtualNetworkInterface(String iName, String vmac, String vip, String bip, String vbw) {
			vMac = vmac;
			vIP = vip;
			bIP = bip;
			virtualBw = vbw;
			intfName = iName;
		}
		
		public String getInterfaceStr() {
			return intfName +","+vIP+","+bIP+","+virtualBw;
		}
	};
	
	private class VirtualNodeContext{
		DotTree.Node virtulNode;
		private String hadoopNode;
		private String vHostName;
		private String cpuSet;
		

		private DiskParition allottedPartition;

		//These two come from virtual node demand
		private short storageSize = 0;
		private short storageIORate = 0;
		
		private short containerSize = 0;
		private short containerIORate = 0;
		
		int hadoopType = 0;
		ArrayList<VirtualNetworkInterface> vIntfs = new ArrayList<VirtualNetworkInterface>();
		
		VirtualNodeContext(DotTree.Node vNode, String phyNodeIP, String cpuSe) {
			allottedPartition = null;
			virtulNode = vNode;
			hadoopNode = virtulNode.attributes.get(HadoopPropertyID);
			String contStr = virtulNode.attributes.get(containerNodePropertyID);
			String storageStr = virtulNode.attributes.get(StorageNodePropertyID);
			if (contStr != null) {
				String[] vals = contStr.split(",");
				containerSize = Short.parseShort(vals[0]);
				containerIORate = Short.parseShort(vals[1]);
			}
			if (storageStr != null) {
				String[] vals = storageStr.split(",");
				storageSize = Short.parseShort(vals[0]);
				storageIORate = Short.parseShort(vals[1]);
			}
			
			cpuSet = cpuSe;
			if (hadoopNode != null) {
				if (hadoopNode.compareTo("namenode") == 0) {
					vHostName = "namenode";
					hadoopType = 1;
				} else if (hadoopNode.compareTo("resourcemanager") == 0) {
					vHostName = "resourcemanager";
					hadoopType = 2;
				}
				else {
					vHostName = getNextSlaveHostName();
					hadoopType = 3;
				}
			}
			else {
				vHostName = getNextSlaveHostName();
			}
		}
		
		public void addVirtualNetworkInterface(String intfName, String vIntfBW, String virtualMac) {
			String vIP = null;
			String bIP = null;
			if (hadoopType == 1)
				vIP = "10.0.10.1/16";
			else if (hadoopType == 2)
				vIP = "10.0.10.2/16";
			else 
				vIP = getNextSlaveIP();
			bIP = getBroadcastIPFromIPandNetMask(vIP);
			VirtualNetworkInterface intf = new VirtualNetworkInterface(intfName, virtualMac, vIP, bIP, vIntfBW);
			vIntfs.add(intf);
		}
		
		public String getStorageAllocationString() {
			if (this.allottedPartition == null) {
				return "0,0";
			}
			String str = this.allottedPartition.getStorageBlockDeviceString()+","+Integer.toString(storageIORate);
			return str;
		}
		
		public String getInterfacesString() {
			String str = new String();
			for(VirtualNetworkInterface vnif : vIntfs ){
				str += vnif.getInterfaceStr() + " ";
			}
			return str;
		}

		public String getContainerAllocationString() {
			String str = Integer.toString(this.containerSize)+","+Integer.toString(this.containerIORate);
			return str;
		}
	};
	
	private class DiskParition {
		public String disk; //e.g sda or sdb
		public short partitionNumber;
		public short partitionSize; //in Gb
		public short partitionOffset; //start offset of the partition in GiB
		public DiskParition(String disk, short partitionNumber, short partitionOffset, short partitionSize) {
			this.disk = disk;
			this.partitionNumber = partitionNumber;
			this.partitionSize = partitionSize;
			this.partitionOffset = partitionOffset;
		}
		
		public String getStorageBlockDeviceString() {
			return ("/dev/"+disk + Integer.toString(partitionNumber));
		}
	};
	
	private class Disk {

		String diskId;
		int storage; //in gb
		int ioRate; //in mbps
		short partitionOffset = 0;
		
		//e.g. >>0GiB,50GiB 50GiB,100GiB <<
		String partitionSeqenceString;

		private short partitionIndex;

		Disk(String dName, int capacity, int iorate) {
			partitionIndex = 1;
			diskId = dName;
			storage = capacity;
			ioRate = iorate;
			partitionSeqenceString = new String();
		}
		
		public DiskParition allocateDiskChunk (short size, int iorate){
			storage -= size;
			ioRate -= iorate;
			String unit = "GiB";
			if (partitionOffset == 0)
				unit = "G";
			DiskParition diskPart = new DiskParition(diskId, partitionIndex, partitionOffset, size);
			partitionSeqenceString += Integer.toString(partitionOffset)+ unit+","+ 
					Integer.toString(partitionOffset+size)+"GiB  ";
			partitionIndex++;
			partitionOffset += size;
			return  diskPart;
		}
		
		public String getPartitionTableCreationString() {
			return concateWithSpace(PhysicalNodeContext.partitionTableFuncName, "/dev/"+diskId, "gpt");
		}
		
		public String getPartitionSeqenceStringString() {
			return concateWithSpace(PhysicalNodeContext.createPartitionsFuncName, "/dev/"+diskId, partitionSeqenceString);
		}
	};

	private class PhysicalStorage {

		//keeps track of start index for the new partition
		//disk id
		HashMap<String, Disk> disksMap;
		PhysicalStorage() {
			disksMap =  new HashMap<String, Disk>();
		}

		public void AddStorage(String id, int size, int iorate){
			if (!disksMap.containsKey(id)) {
				disksMap.put(id, new Disk(id, size, iorate));
			}
		}
		
		public DiskParition allocateStorage(short size, int iorate) {
			DiskParition disk_partition = null;

			for(Map.Entry<String, Disk> entry : disksMap.entrySet()) {
				Disk disk = entry.getValue();
				if (disk.ioRate > iorate && disk.storage > size) {
					disk_partition = entry.getValue().allocateDiskChunk(size, iorate);
					break;
				}
			}
			if (disk_partition == null) {
				System.out.println("Error: Could not allocate storage for size :"+ Integer.toString(size)+
						"iorate : "+ Integer.toString(iorate));
			}
			return disk_partition;
		}
		
		public ArrayList<String> getStringsToCreatePartitionTable() {
			ArrayList<String> partitionTableCreation = new ArrayList<String>();
			for(Map.Entry<String, Disk> entry : disksMap.entrySet()) {
				Disk disk = entry.getValue();
				if (disk.partitionOffset == 0) continue;
				partitionTableCreation.add(disk.getPartitionTableCreationString());
				partitionTableCreation.add(disk.getPartitionSeqenceStringString());
			}
			return partitionTableCreation;
		}
	};
	
	private class PhysicalNodeContext {
		
		private DotTree.Node physicalNode;
		private PhysicalStorage storage;
		private PhysicalStorage containerPool;
		
		private static final String mgmtTunIfName = "mgmt";
		private static final String tunIfName = "tun";
		private static final String vethIfName = "veth";
		private static final String tapIfName = "tap";
		private static final String switchName = "switch";
		private static final String loopbackIPAddr = "127.0.0.1";
		
		//these constants are depended on python script file
		private static final String tunnelFuncName = "create_tunnel_endpoint";
		private static final String bridgeFuncName = "create_ovs_bridge";
		private static final String ovsContFuncName = "launch_ovs_container";
		private static final String qosFuncName = "set_QoS_on_interface";
		
		private static final String createVirtualNodeFuncName = "create_virtual_node";
		private static final String createPartitionsFuncName = "create_partitions";
		private static final String partitionTableFuncName = "create_partition_table";
		private static final String ovsBuildPath = "/root/ovs230build/";
		private static final String mgmtBridgeTunFuncName = "create_mgmt_bridge_with_tunnel_endpoint";
		private static final String managerBridgeFuncName = "create_manager_bridge";
		private static final String vethPCreationFuncName = "create_veth_pair";
		private static final String dockerOVSImageName = "hsoni/fc21-ovs-public:v1";
		private static final String dockerHadoopImageName = "hsoni/hadoop:v14";

		
		//cleanup virtual network
		private static final String dTunnelFuncName = "delete_tunnel_endpoint";
		private static final String dBridgeFuncName = "delete_ovs_bridge";
		private static final String dContFuncName = "delete_container";
		private static final String dVHostContFuncName = "delete_vhost_container";
		private static final String dTapFuncName = "delete_tap_device";
		
		private static final String dmgmtBridgeTunFuncName = "delete_mgmt_bridge_with_tunnel_endpoint";
		private static final String dManagerBridgeFuncName = "delete_manager_bridge";
		private static final String dVethPFuncName = "delete_veth_pair";
	
		
		private short tunIfIndex;
		private short tapIfIndex;
		private short switchIndex;
		private short mgmtTunIfIndex;
		private short vethIfIndex = 1;
		
		//CPU set number
		private short cpuset_nuumber = 1;
		
		//following 3 can be moved to different class and
		// create a hashmap with physical node-id key, supply the value.. later
		private int udpPortNumber;
		private int sessionID;
		private int tunnelID;
		
		private String nodeId;
		private String nodeIP;
			
		//Map  HashMap<virtual Node id, IntfName
		//Only virtual switches are stored
		private HashMap<String, ArrayList<String>> vNodeToVIntfsMap;
		
		//This array contains commands to delete tunnels,
		//veth pairs are deleted using 
		private ArrayList<String> deleteCommandLines = null;
		private ArrayList<String> commandLines = null;
		public HashMap<String, VirtualNodeContext> virtualHostContexts = null;
		public ArrayList<String> virtualConfigCommandStrs = null;
		
		public boolean containsNamenode = false;
		public boolean containsResoureManager= false;
		
		
		PhysicalNodeContext (DotTree.Node pNode) {
			physicalNode = pNode;
			vNodeToVIntfsMap = new HashMap<String, ArrayList<String> >();
			commandLines = new ArrayList<String>();
			deleteCommandLines = new ArrayList<>();
			virtualConfigCommandStrs = new ArrayList<String>();
			virtualHostContexts = new HashMap<String, VirtualNodeContext>();
			tunIfIndex = 1;
			tapIfIndex = 1;
			udpPortNumber = 50000;
			sessionID = 5000;
			tunnelID = 5000;
			nodeId = pNode.id;
			nodeIP = findPropValueOfNode(IPNodePropertyID);
			switchIndex = 0;
			mgmtTunIfIndex = 1;
			storage = null;
			containerPool = null;
			getContainerStorageFromPhysicalNode(pNode);
			getDiskStorageFromPhysicalNode(pNode);
		}
		
		private void getContainerStorageFromPhysicalNode(DotTree.Node pNode) {
			String[] vals;
			String contProp = pNode.attributes.get(containerNodePropertyID);
			if (contProp != null) {
				vals = contProp.split(",");
				containerPool = new PhysicalStorage();
				containerPool.AddStorage("containerpool", Integer.parseInt(vals[0]), Integer.parseInt(vals[1]));
			}
		}
		
		private void getDiskStorageFromPhysicalNode(DotTree.Node pNode) {
			ArrayList<String> disks = new ArrayList<String>();
			for(Map.Entry<String, String> entry : pNode.attributes.entrySet()) {
				if(entry.getKey().startsWith("disk")) {
					disks.add(entry.getValue());
				}
			}
			if (!disks.isEmpty())
				storage = new PhysicalStorage();
			for(String str : disks) {
				String[] attrs = str.split(",");
				if (attrs.length != 3) {
					System.out.println("Error : something is missing here : " + str);
				}
				storage.AddStorage(attrs[0], Integer.parseInt(attrs[1]), Integer.parseInt(attrs[2])); 
			}
		}

		private String findPropValueOfNode(String property)  {
			String propValue = null;
			propValue = physicalNode.attributes.get(property);
			return propValue;
		}
		
		private String getNextCPUSet (short nCPU) {
			String str = "";
			short i = 0;
			for (i=0 ; i<nCPU-1 ; i++) {
				str += Integer.toString(cpuset_nuumber++) +  ",";
			}
			str += Integer.toString(cpuset_nuumber++);
			return str;
		}
		
		public PeerMetadata getNextMetaDataForPeer() {
			PeerMetadata data = new PeerMetadata(nodeIP,  Integer.toString(++udpPortNumber), 
					Integer.toString(++sessionID), Integer.toString(++tunnelID) );
			return data;
		}
		
		public void addVirtualSwitchInterface(DotTree.Node vNode, String vIntfBW, PeerMetadata pData) {
			System.out.println("Add  Virtual Switch Interface "+ vNode.id );

			String intfNStr = tunIfName + Integer.toString(tunIfIndex++);
			String tunIdStr = Integer.toString(tunnelID);
			String udpPortStr = Integer.toString(udpPortNumber);
			String sidStr = Integer.toString(sessionID);
			
			String tunnelCmd = concateWithSpace(tunnelFuncName, intfNStr, tunIdStr, pData.TunnelID, nodeIP, pData.IP, 
					udpPortStr, pData.UDPPort, sidStr, pData.SessionID, getNextVirtualSwitchIntfMac());		
			commandLines.add(tunnelCmd);

			String intf = intfNStr+","+vIntfBW;
			if (!vNodeToVIntfsMap.containsKey(vNode.id)) {
				ArrayList<String> intfs = new ArrayList<String>();
				intfs.add(intf);
				vNodeToVIntfsMap.put(vNode.id, intfs);
			} else {
				vNodeToVIntfsMap.get(vNode.id).add(intf);
			}
			
			String dTunnelCmd = concateWithSpace(dTunnelFuncName, sidStr, tunIdStr, intfNStr);
			deleteCommandLines.add(dTunnelCmd);
		}
		
		public void addVirtualHost(DotTree.Node vNode, String vIntfBW, PeerMetadata pData) {
			System.out.println("Add  Virtual host "+ vNode.id );

			String intfNStr = tunIfName + Integer.toString(tunIfIndex++);
			String tunIdStr = Integer.toString(tunnelID);
			String udpPortStr = Integer.toString(udpPortNumber);
			String sidStr = Integer.toString(sessionID);
			String hostMac = getNextVirtualHostMac();
			
			String nCpuStr = vNode.attributes.get(CPUNodePropertyID);
			String cpuset = getNextCPUSet((short) Integer.parseInt(nCpuStr));
			
			String tunnelCmd = concateWithSpace(tunnelFuncName, intfNStr, tunIdStr, pData.TunnelID, nodeIP, pData.IP, 
					udpPortStr, pData.UDPPort, sidStr, pData.SessionID, hostMac);		
			commandLines.add(tunnelCmd);
			String deleteTunnelCmd = concateWithSpace(dTunnelFuncName, sidStr, tunIdStr, intfNStr);
			deleteCommandLines.add(deleteTunnelCmd);

			if (!virtualHostContexts.containsKey(vNode.id)) {
				VirtualNodeContext  virtualContext = new VirtualNodeContext(vNode, nodeIP, cpuset);
				virtualContext.addVirtualNetworkInterface(intfNStr, vIntfBW, hostMac);
				virtualHostContexts.put(vNode.id, virtualContext);
			} else {
				virtualHostContexts.get(vNode.id).addVirtualNetworkInterface(intfNStr, vIntfBW, hostMac);;
			}
			
			String hadoopNode = vNode.attributes.get(HadoopPropertyID);
			if (hadoopNode != null) {
				if (hadoopNode.compareTo("namenode") == 0) {
					containsNamenode = true;
				} 
				if (hadoopNode.compareTo("resourcemanager") == 0) {
					containsResoureManager = true;
				}
			}
		}
		
		public void addAdjacentVirtualSwicthes(DotTree.Node vxSwitchNode, DotTree.Node vySwitchNode, String vIntfBW) {
			System.out.println("Add Adjacent Virtual Swicthes "+ vxSwitchNode.id + " " +vySwitchNode.id);
			
			String intfNStr = vxSwitchNode.id +  "-" + vethIfName + Integer.toString(vethIfIndex);
			String pIntfNStr = vySwitchNode.id + "-" + vethIfName + Integer.toString(vethIfIndex);
			vethIfIndex++;
			
			String vethCmd;			
			vethCmd = concateWithSpace(vethPCreationFuncName, intfNStr, pIntfNStr, 
					getNextVirtualSwitchIntfMac(), getNextVirtualSwitchIntfMac());

			commandLines.add(vethCmd);

			String intf = intfNStr+","+vIntfBW;
			if (!vNodeToVIntfsMap.containsKey(vxSwitchNode.id)) {
				ArrayList<String> intfs = new ArrayList<String>();
				intfs.add(intf);
				vNodeToVIntfsMap.put(vxSwitchNode.id, intfs);
			} else {
				vNodeToVIntfsMap.get(vxSwitchNode.id).add(intf);
			}
			
			String intfp = pIntfNStr+","+vIntfBW;
			if (!vNodeToVIntfsMap.containsKey(vySwitchNode.id)) {
				ArrayList<String> intfs = new ArrayList<String>();
				intfs.add(intfp);
				vNodeToVIntfsMap.put(vySwitchNode.id, intfs);
			} else {
				vNodeToVIntfsMap.get(vySwitchNode.id).add(intfp);
			}
		}
		
		public void addAdjacentVirtualHostSwitch(DotTree.Node vHostNode, DotTree.Node vSwitchNode, String vIntfBW) {
			System.out.println("Add Adjacent Virtual host Switch "+ vHostNode.id + " " +vSwitchNode.id);
			String intfNStr = vHostNode.id +  "-" + vethIfName + Integer.toString(vethIfIndex);
			String pIntfNStr = vSwitchNode.id + "-" + vethIfName + Integer.toString(vethIfIndex);
			vethIfIndex++;
			
			String nCpuStr = vHostNode.attributes.get(CPUNodePropertyID);
			String cpuset = getNextCPUSet((short) Integer.parseInt(nCpuStr));
			String hostMac = getNextVirtualHostMac();

			String vethCmd = concateWithSpace(vethPCreationFuncName, intfNStr, pIntfNStr, 
					hostMac, getNextVirtualSwitchIntfMac());
			
			commandLines.add(vethCmd);
			
			String intf = pIntfNStr+","+vIntfBW;
			if (!vNodeToVIntfsMap.containsKey(vSwitchNode.id)) {
				ArrayList<String> intfs = new ArrayList<String>();
				intfs.add(intf);
				vNodeToVIntfsMap.put(vSwitchNode.id, intfs);
			} else {
				vNodeToVIntfsMap.get(vSwitchNode.id).add(intf);
			}
			
			VirtualNodeContext virtualContext = null;
			if (!virtualHostContexts.containsKey(vHostNode.id)) {
				virtualContext = new VirtualNodeContext(vHostNode, nodeIP, cpuset);
				virtualContext.addVirtualNetworkInterface(intfNStr, vIntfBW, hostMac);
				virtualHostContexts.put(vHostNode.id, virtualContext);
			} else {
				virtualHostContexts.get(vHostNode.id).addVirtualNetworkInterface(intfNStr, vIntfBW, hostMac);;
			}
			
			String hadoopNode = vHostNode.attributes.get(HadoopPropertyID);
			if (hadoopNode != null) {
				if (hadoopNode.compareTo("namenode") == 0) {
					containsNamenode = true;
				} 
				if (hadoopNode.compareTo("resourcemanager") == 0) {
					containsResoureManager = true;
				}
			}
		}
		
		public void allocateStorageToVirtualNodes() {
			if (storage == null) return;
			for(Map.Entry<String, VirtualNodeContext> entry : virtualHostContexts.entrySet()) {
				VirtualNodeContext vnc = entry.getValue();
				if (vnc.storageSize == 0 ||  vnc.storageIORate == 0)
					continue;
				vnc.allottedPartition = storage.allocateStorage(vnc.storageSize, vnc.storageIORate);
			}
			commandLines.addAll(0, storage.getStringsToCreatePartitionTable());
		}
		
		public void allocateContainerToVirtualNodes() {
			if (containerPool == null) {
				for(Map.Entry<String, VirtualNodeContext> entry : virtualHostContexts.entrySet()) {
					VirtualNodeContext vnc = entry.getValue();
					vnc.containerSize = 0; 
					vnc.containerIORate = 0;
				}
			} else {
				for(Map.Entry<String, VirtualNodeContext> entry : virtualHostContexts.entrySet()) {
					VirtualNodeContext vnc = entry.getValue();
					if (vnc.containerSize == 0 ||  vnc.containerIORate == 0)
						continue;
					containerPool.allocateStorage(vnc.containerSize, vnc.containerIORate);
				}
			}
		}
		
		//create_ovs_bridge  ovs_build_path  switch_name  dpid  sdn_controller_ip_port  if1  if2  if3
		public void createOVSCommandForVirtualSwithces() {
			
			for(Map.Entry<String, ArrayList<String>> entry : vNodeToVIntfsMap.entrySet()) {
				String swName = entry.getKey();
				String dpid = ConfigGenerator.getNextDPId();
				String intfs = new String();
				String cpus = findCPUPropOfNodeFromGraph(swName, virtualNet);
				String cpuset = getNextCPUSet((short) Integer.parseInt(cpus));
				String container = findPropOfNodeFromGraph(containerNodePropertyID, swName, virtualNet);
				if (containerPool == null || container == null) {
					container = new String("0,0");
				} else {
					String[] contVals = container.split(",");
					short size = Short.parseShort(contVals[0]);
					short iorate = Short.parseShort(contVals[1]);
					containerPool.allocateStorage(size, iorate);
				}
				
				for (String str : entry.getValue()) {
					intfs += " "  + str; 
				}
				
				String cmd = concateWithSpace(ovsContFuncName, dockerOVSImageName, swName, cpuset, 
						container, dpid, managerIP+":"+OFPort.toString(), intfs) ;
				commandLines.add(cmd);
				String dcmd = concateWithSpace(dContFuncName, swName, "0,0");
				deleteCommandLines.add(dcmd);
			}
		}
		
		public void createVHostContainerCommandForVirtualNodes() {
			for(Map.Entry<String, VirtualNodeContext> entry : virtualHostContexts.entrySet()) {
				VirtualNodeContext vnc = entry.getValue();
				String vNodeCmd = concateWithSpace(createVirtualNodeFuncName, 
						dockerHadoopImageName, 
						vnc.virtulNode.id, 
						vnc.cpuSet, 
						vnc.getStorageAllocationString(),
						vnc.getContainerAllocationString(),
						vnc.vHostName, 
						Integer.toString(virtualHostSlaveIndex), 
						vnc.getInterfacesString());
				commandLines.add(vNodeCmd);
				String dcmd = concateWithSpace(dContFuncName, vnc.virtulNode.id, 
						vnc.getStorageAllocationString());
				deleteCommandLines.add(dcmd);
			}
		}
		
		public String generateCommandToFile (String dir) {
			boolean rmflag = false, nnfalg =false; 
			FileOutputStream fs;
			String nline ="", rmline="";
			String fileName = dir+"/"+nodeIP + ".cfg";
			try {
				fs = new FileOutputStream(fileName);
				BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fs));
				for(String line : commandLines ){
					if (line.contains("namenode")) {
						nline = line;
						nnfalg = true;
						continue;
					}
					if (line.contains("resourcemanager")) {
						rmline = line;
						rmflag = true;
						continue;
					}
					bw.write(line);
					bw.newLine();
				}
				if (rmflag) { bw.write(rmline);bw.newLine(); }
				if (nnfalg) { bw.write(nline);bw.newLine(); }
				bw.close();
			} catch (Exception e) {
				System.out.println("Exception thrown: error in writing file named - " + fileName);
			}
			return fileName;
		}
		
		public String generateDeleteCommandToFile(String dir) {
			FileOutputStream fs;
			String dFileName = dir+"/d-"+nodeIP + ".cfg";
			try {
				fs = new FileOutputStream(dFileName);
				BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fs));
				
				for(String line : deleteCommandLines ){
					bw.write(line);
					bw.newLine();
				}
				bw.close();
			} catch (Exception e) {
				System.out.println("Exception thrown: error in writing file named - " + dFileName);
			}
			return dFileName;
		}
	};
	
	public static String concateWithSpace(String ... list) {
		StringBuilder cmdStrBuilder = new StringBuilder();
		for (int i=0; i<list.length; i++) {
			cmdStrBuilder.append(list[i]);
			cmdStrBuilder.append(" ");
		}
		return cmdStrBuilder.toString();
	}
	
	private class PeerMetadata {
		public String IP;
		public String UDPPort;
		public String SessionID;
		public String TunnelID;
		
		PeerMetadata (String ip, String port, String sid, String tid) {
			IP = ip;
			UDPPort = port;
			SessionID = sid;
			TunnelID = tid;
		}
	};
	
}
