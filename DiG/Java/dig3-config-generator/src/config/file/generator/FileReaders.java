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

package config.file.generator;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import org.antlr.runtime.ANTLRInputStream;
import org.antlr.runtime.CommonTokenStream;
import org.antlr.runtime.tree.CommonTree;
import org.antlr.runtime.tree.CommonTreeNodeStream;
import org.cesta.parsers.dot.DotLexer;
import org.cesta.parsers.dot.DotParser;
import org.cesta.parsers.dot.DotTree;
import org.cesta.parsers.dot.DotParser.graph_return;

/**
 * @author Hardik Soni
 *
 */
public class FileReaders {
	
	public static DotTree.Graph GetDotTreeGraphFromFile (String dotFileName) {		
		DotTree.Graph graphObjRet = null;
		FileInputStream file;
		try {
			file = new FileInputStream(dotFileName);		
			ANTLRInputStream input = new ANTLRInputStream(file);
			DotLexer lexer = new DotLexer(input);
			CommonTokenStream tokens = new CommonTokenStream(lexer);
			
			DotParser parser = new DotParser(tokens);
			graph_return ret = parser.graph();
			CommonTree tree = ret.getTree();
			CommonTreeNodeStream ctnsNodes = new CommonTreeNodeStream(tree);
			DotTree dotTree = new DotTree(ctnsNodes);
			graphObjRet = dotTree.graph().graphObj;
			
			removeQuotesFromPropertyValueOfGrpah(graphObjRet);
			System.out.println (graphObjRet.id);
			
			for (DotTree.Node n : graphObjRet.getNodes()) {
				System.out.println (n.toString());
			}
			
			for (DotTree.NodePair np : graphObjRet.getNodePairs()) {
				System.out.println (np.toString());
			}
			
		} catch (Exception e) {
			System.out.println("error in reading file named - "+dotFileName);
			//e.printStackTrace();
		}
		return graphObjRet;
	}
	
	private static void removeQuotesFromPropertyValueOfGrpah(DotTree.Graph graphObj)  {
		for (Map.Entry<String, DotTree.Node> en1 : graphObj.nodes.entrySet()) {
			for (Map.Entry<String, String> en2 : en1.getValue().attributes.entrySet()) {
				String str = en2.getValue();
				if (str.length() > 2 && str.startsWith("\"") && str.endsWith("\"")) {
					str = str.substring(1,str.length()-1);
					en2.setValue(str);
				}
			}
		}
	}

	public static HashMap<String, ArrayList<String>> GetMappingsFromFile (String mappingFileName) {
		HashMap<String, ArrayList<String>> mapping = new HashMap<String, ArrayList<String>> ();
		FileInputStream fs;
		try {
			fs = new FileInputStream(mappingFileName);
			BufferedReader br = new BufferedReader(new InputStreamReader(fs));
			
			String physNodeId = null;
			String line = null;
			String[] nodeIds = null;
			String[] vtNodeIds = null;

			while ((line = br.readLine()) != null) {
				ArrayList<String> vtNodeIdsArrayList = new ArrayList<String>();
				nodeIds = line.split("-");
				
				if (nodeIds.length != 2) {
					System.out.println("error in file named - "+mappingFileName + " at line : --" +line);
					System.out.println("error in reading file named - "+mappingFileName);
					return null;
				}
				
				physNodeId = nodeIds[0].trim();
				vtNodeIds = nodeIds[1].trim().split(",");
				for (String id : vtNodeIds) {
					vtNodeIdsArrayList.add(id.trim());
				}
				mapping.put(physNodeId, vtNodeIdsArrayList);
			}
		 
			br.close();
		} catch (Exception e) {
			System.out.println("Exception thrown: error in reading file named - "+mappingFileName);
		}
		return mapping;
	}
}
