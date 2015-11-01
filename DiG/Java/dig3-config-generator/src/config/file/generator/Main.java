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

import java.util.ArrayList;
import java.util.HashMap;

import org.cesta.parsers.dot.DotTree;

public class Main {

	public static void main(String[] args) {
		if (args.length != 4) {
			String usgae = "4 arguments are required: \n" + 
					"1) DOT file of physical network with IP annotated \n" +
					"2) DOT file of virtual network with IP annotated \n" +
					"3) DOT file of mapping file \n"+
					"	mapping file format - one line per physical node with following format \n" +
					"		<physical node id1> - <virtual node id1>, <virtual node id2>...  \n"+
					"		<physical node id2> - <virtual node id11>, <virtual node id21>...  \n"+
					"4) Location of output files \n";
			System.out.println(usgae);
			return;
		}
		
		
		DotTree.Graph physicalNet = FileReaders.GetDotTreeGraphFromFile(args[0]);
		DotTree.Graph virtualNet = FileReaders.GetDotTreeGraphFromFile(args[1]);
		
		HashMap<String, ArrayList<String>> mapping = FileReaders.GetMappingsFromFile(args[2]);
		
		ConfigGenerator cfgFileGenerator = new ConfigGenerator(physicalNet, virtualNet, mapping);
		String dir = args[3];
		cfgFileGenerator.generateAllFiles(dir);
	}
}
