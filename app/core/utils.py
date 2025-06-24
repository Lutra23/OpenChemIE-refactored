import numpy as np
from PIL import Image
import cv2
import layoutparser as lp
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import rdDepictor
rdDepictor.SetPreferCoordGen(True)
from rdkit.Chem.Draw import IPythonConsole
from rdkit.Chem import AllChem
import re
import copy

BOND_TO_INT = {
    "": 0,
    "single": 1,
    "double": 2, 
    "triple": 3, 
    "aromatic": 4, 
    "solid wedge": 5, 
    "dashed wedge": 6
}

RGROUP_SYMBOLS = ['R', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12',
                  'Ra', 'Rb', 'Rc', 'Rd', 'Rf', 'X', 'Y', 'Z', 'Q', 'A', 'E', 'Ar', 'Ar1', 'Ar2', 'Ari', "R'", 
                  '1*', '2*','3*', '4*','5*', '6*','7*', '8*','9*', '10*','11*', '12*','[a*]', '[b*]','[c*]', '[d*]']

RGROUP_SYMBOLS = RGROUP_SYMBOLS + [f'[{i}]' for i in RGROUP_SYMBOLS]

RGROUP_SMILES = ['[1*]', '[2*]','[3*]', '[4*]','[5*]', '[6*]','[7*]', '[8*]','[9*]', '[10*]','[11*]', '[12*]','[a*]', '[b*]','[c*]', '[d*]','*', '[Rf]']

def get_figures_from_pages(pages, pdfparser):
    figures = []
    for i in range(len(pages)):
        img = np.asarray(pages[i])
        layout = pdfparser.detect(img)
        blocks = lp.Layout([b for b in layout if b.type == "Figure"])
        for block in blocks:
            figure = Image.fromarray(block.crop_image(img))
            figures.append({
                'image': figure,
                'page': i
            })
    return figures

def clean_bbox_output(figures, bboxes):
    results = []
    cropped = []
    references = []
    for i, output in enumerate(bboxes):
        mol_bboxes = [elt['bbox'] for elt in output if elt['category'] == '[Mol]']
        mol_scores = [elt['score'] for elt in output if elt['category'] == '[Mol]']
        data = {}
        results.append(data)
        data['image'] = figures[i]
        data['molecules'] = []
        for bbox, score in zip(mol_bboxes, mol_scores):
            x1, y1, x2, y2 = bbox
            height, width, _ = figures[i].shape
            cropped_img = figures[i][int(y1*height):int(y2*height),int(x1*width):int(x2*width)]
            cur_mol = {
                'bbox': bbox,
                'score': score,
                'image': cropped_img,
                #'info': None,
            }
            cropped.append(cropped_img)
            data['molecules'].append(cur_mol)
            references.append(cur_mol)
    return results, cropped, references
    
def convert_to_pil(image):
    if type(image) == np.ndarray:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
    return image

def convert_to_cv2(image):
    if type(image) != np.ndarray:
        image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
    return image

def replace_rgroups_in_figure(figures, results, coref_results, molscribe, batch_size=16):
    pattern = re.compile('(?P<name>[RXY]\d?)[ ]*=[ ]*(?P<group>\w+)')
    for figure, result, corefs in zip(figures, results, coref_results):
        r_groups = []
        seen_r_groups = set()
        for bbox in corefs['bboxes']:
            if bbox['category'] == '[Idt]':
                for text in bbox['text']:
                    res = pattern.search(text)
                    if res is None:
                        continue
                    name = res.group('name')
                    group = res.group('group')
                    if (name, group) in seen_r_groups:
                        continue
                    seen_r_groups.add((name, group))
                    r_groups.append({name: res.group('group')})
        if r_groups and result['reactions']:
            seen_r_groups = set([pair[0] for pair in seen_r_groups])
            orig_reaction = result['reactions'][0]
            graphs = get_atoms_and_bonds(figure['figure']['image'], orig_reaction, molscribe, batch_size=batch_size)
            relevant_locs = {}
            for i, graph in enumerate(graphs):
                to_add = []
                for j, atom in enumerate(graph['chartok_coords']['symbols']):
                    if atom[1:-1] in seen_r_groups:
                        to_add.append((atom[1:-1], j))
                relevant_locs[i] = to_add

            for r_group in r_groups:
                reaction = get_replaced_reaction(orig_reaction, graphs, relevant_locs, r_group, molscribe)
                to_add ={
                    'reactants': reaction['reactants'][:],
                    'conditions': orig_reaction['conditions'][:],
                    'products': reaction['products'][:]
                }
                result['reactions'].append(to_add)
    return results

def process_tables(figures, results, molscribe, batch_size=16):
    r_group_pattern = re.compile(r'^(\w+-)?(?P<group>[\w-]+)( \(\w+\))?$')
    for figure, result in zip(figures, results):
        result['page'] = figure['page']
        if figure['table']['content'] is not None:
            content = figure['table']['content']
            if len(result['reactions']) > 1:
                print("Warning: multiple reactions detected for table")
            elif len(result['reactions']) == 0:
                continue
            orig_reaction = result['reactions'][0]
            graphs = get_atoms_and_bonds(figure['figure']['image'], orig_reaction, molscribe, batch_size=batch_size)
            relevant_locs = find_relevant_groups(graphs, content['columns'])
            conditions_to_extend = []
            for row in content['rows']:
                r_groups = {}
                expanded_conditions = orig_reaction['conditions'][:]
                replaced = False
                for col, entry in zip(content['columns'], row):
                    if col['tag'] != 'alkyl group':
                        expanded_conditions.append({
                            'category': '[Table]',
                            'text': entry['text'], 
                            'tag': col['tag'],
                            'header': col['text'],
                        })
                    else:
                        found = r_group_pattern.match(entry['text'])
                        if found is not None:
                            r_groups[col['text']] = found.group('group')
                            replaced = True
                reaction = get_replaced_reaction(orig_reaction, graphs, relevant_locs, r_groups, molscribe)  
                if replaced:
                    to_add = {
                        'reactants': reaction['reactants'][:],
                        'conditions': expanded_conditions,
                        'products': reaction['products'][:]
                    }
                    result['reactions'].append(to_add)
                else:
                    conditions_to_extend.append(expanded_conditions)
            orig_reaction['conditions'] = [orig_reaction['conditions']]
            orig_reaction['conditions'].extend(conditions_to_extend)
    return results


def get_atoms_and_bonds(image, reaction, molscribe, batch_size=16):
    image = convert_to_cv2(image)
    cropped_images = []
    results = []
    for key, molecules in reaction.items():
        for i, elt in enumerate(molecules):
            if type(elt) != dict or elt['category'] != '[Mol]':
                continue
            x1, y1, x2, y2 = elt['bbox']
            height, width, _ = image.shape
            cropped_images.append(image[int(y1*height):int(y2*height),int(x1*width):int(x2*width)])
            to_add = {
                'image': cropped_images[-1],
                'chartok_coords': {
                    'coords': [],
                    'symbols': [],
                },
                'edges': [],
                'key': (key, i)
            }
            results.append(to_add)
    outputs = molscribe.predict_images(cropped_images, return_atoms_bonds=True, batch_size=batch_size)
    for mol, result in zip(outputs, results):
        for atom in mol['atoms']:
            result['chartok_coords']['coords'].append((atom['x'], atom['y']))
            result['chartok_coords']['symbols'].append(atom['atom_symbol'])
        result['edges'] = [[0] * len(mol['atoms']) for _ in range(len(mol['atoms']))]
        for bond in mol['bonds']:
            i, j = bond['endpoint_atoms']
            result['edges'][i][j] = BOND_TO_INT[bond['bond_type']]
            result['edges'][j][i] = BOND_TO_INT[bond['bond_type']]
    return results

def find_relevant_groups(graphs, columns):
    results = {}
    r_groups = set([f"[{col['text']}]" for col in columns if col['tag'] == 'alkyl group'])
    for i, graph in enumerate(graphs):
        to_add = []
        for j, atom in enumerate(graph['chartok_coords']['symbols']):
            if atom in r_groups:
                to_add.append((atom[1:-1], j))
        results[i] = to_add
    return results

def get_replaced_reaction(orig_reaction, graphs, relevant_locs, mappings, molscribe):
    graph_copy = []
    for graph in graphs:
        graph_copy.append({
            'image': graph['image'],
            'chartok_coords': {
                'coords': graph['chartok_coords']['coords'][:],
                'symbols': graph['chartok_coords']['symbols'][:],
            },
            'edges': graph['edges'][:],
            'key': graph['key'],
        })
    for graph_idx, atoms in relevant_locs.items():
        for atom, atom_idx in atoms:
            if atom in mappings:
                graph_copy[graph_idx]['chartok_coords']['symbols'][atom_idx] = mappings[atom]
    reaction_copy = {}
    def append_copy(copy_list, entity):    
        if entity['category'] == '[Mol]':
            copy_list.append({
                k1: v1 for k1, v1 in entity.items()
            })
        else:
            copy_list.append(entity)

    for k, v in orig_reaction.items():
        reaction_copy[k] = []
        for entity in v:
            if type(entity) == list:
                sub_list = []
                for e in entity:
                    append_copy(sub_list, e)
                reaction_copy[k].append(sub_list)
            else:
                append_copy(reaction_copy[k], entity)

    for graph in graph_copy:
        output = molscribe.convert_graph_to_output([graph], [graph['image']])
        molecule = reaction_copy[graph['key'][0]][graph['key'][1]]
        molecule['smiles'] = output[0]['smiles']
    return reaction_copy

def get_sites(tar, ref, ref_site = False):
    """
    Returns sites for R-group substitution given a molecule to be substituted and a reference for substitution sites
    """
    if ref_site:
        ref_mol_sites = Chem.MolFromSmiles(ref)
        patt = Chem.MolFromSmarts('[*]')
        sites = ref_mol_sites.GetSubstructMatches(patt)
    else:
        ref_mol = Chem.MolFromSmiles(ref)
        sites = tar.GetSubstructMatches(ref_mol)
    return sites


def get_atom_mapping(prod_mol, prod_smiles, r_sites_reversed = None):
    # returns prod_mol_to_query which is the mapping of atom indices in prod_mol to the atom indices of the molecule represented by prod_smiles
    prod_smi_mol = Chem.MolFromSmiles(prod_smiles)
    if prod_smi_mol is None:
        return None, None, None, None
    prod_smi_mol_no_r = Chem.MolFromSmiles(re.sub('\[\w*\*\]', '*', prod_smiles))
    patt = Chem.MolFromSmiles('[*]')
    r_sites = prod_smi_mol.GetSubstructMatches(patt)
    if r_sites_reversed is None:
        r_sites_reversed = {}
        for i in range(len(r_sites)):
            r_sites_reversed[r_sites[i][0]] = i
    
    prod_mol_substruct = prod_mol.GetSubstructMatches(prod_smi_mol_no_r)
    #if not prod_mol_substruct:
    #    prod_smi_mol_no_r_no_charge = Chem.MolFromSmiles(re.sub('([+-])', '', re.sub('\[\w*\*\]', '*', prod_smiles)))
    #    prod_mol_substruct = prod_mol.GetSubstructMatches(prod_smi_mol_no_r_no_charge)
    prod_mol_to_query_list = []
    query_to_prod_mol_list = []
    if not prod_mol_substruct:
        print("Substructure match in atom mapping not found")
        # print(prod_smiles)
        # return None, None, None, None
        # return {}, {}, prod_mol, {}
        prod_smi_mol = Chem.MolFromSmiles(prod_smiles)
        prod_mol = Chem.AddHs(prod_mol)
        prod_smi_mol = Chem.AddHs(prod_smi_mol)
        prod_mol_substruct = prod_mol.GetSubstructMatches(prod_smi_mol)
        if not prod_mol_substruct:
            print("Still no substructure match")
            return {}, {}, prod_mol, {}

    for prod_coords in prod_mol_substruct:
        prod_mol_to_query = {}
        query_to_prod_mol = {}
        for i, atom in enumerate(prod_coords):
            prod_mol_to_query[atom] = i
            query_to_prod_mol[i] = atom
        prod_mol_to_query_list.append(prod_mol_to_query)
        query_to_prod_mol_list.append(query_to_prod_mol)
    return prod_mol_to_query_list, query_to_prod_mol_list, prod_mol, r_sites_reversed


def clean_corefs(coref_results_dict, idx):
    if len(coref_results_dict) <= idx:
        return None
    res = coref_results_dict[idx]
    if 'mol_bboxes' not in res.keys():
        return None
    mol_bboxes_text = []
    if 'smiles' in res['mol_bboxes'][0].keys():
        mol_bboxes_text = [(bbox, bbox['smiles']) for bbox in res['mol_bboxes']]

    if 'idt_bboxes' not in res.keys() or type(res['idt_bboxes']) is not list:
        return None
    idt_bboxes_text = [bbox['text'] for bbox in res['idt_bboxes']]
    
    patt = re.compile('(?P<label>[\w\d\.]+[abc]?)[,:]?[ ]+(?P<group>[\[\]\w\d-]+)')
    coref_smiles = {}
    for text in idt_bboxes_text:
        found = patt.finditer(text)
        if found is not None:
            for f in found:
                coref_smiles[f.group('label')] = f.group('group')
    return mol_bboxes_text, coref_smiles, res['bboxes']

def expand_r_group_label_helper(res, coref_smiles_to_graphs, other_prod, molscribe):
    other_prod_mol = Chem.MolFromSmiles(other_prod[1])
    patt = Chem.MolFromSmarts('[*]')
    match_indices = other_prod_mol.GetSubstructMatches(patt)

    # for each match index, get connected components
    seen_idx = set()
    for match_idx in match_indices:
        match_idx = match_idx[0]
        if match_idx in seen_idx:
            continue
        seen_idx.add(match_idx)
        # get component
        q = [other_prod_mol.GetAtomWithIdx(match_idx).GetNeighbors()[0].GetIdx()]
        seen_q = set(q)
        head = 0
        while head < len(q):
            cur = q[head]
            head += 1
            for neighbor in other_prod_mol.GetAtomWithIdx(cur).GetNeighbors():
                if neighbor.GetIdx() not in seen_q and neighbor.GetIdx() not in seen_idx:
                    q.append(neighbor.GetIdx())
                    seen_q.add(neighbor.GetIdx())
        
        # for component, replace with new r-group
        edit_mol = Chem.RWMol(other_prod_mol)
        r_group_idx = edit_mol.AddAtom(Chem.Atom(0))
        for idx in q:
            edit_mol.ReplaceAtom(idx, Chem.Atom(0))
            edit_mol.GetAtomWithIdx(r_group_idx).SetProp('dummyLabel', other_prod_mol.GetAtomWithIdx(idx).GetSymbol())

        # for component, get smiles
        sub_mol = Chem.PathToSubmol(other_prod_mol, q)
        smiles = Chem.MolToSmiles(sub_mol)
        if smiles in coref_smiles_to_graphs.keys():
            res_to_add = copy.deepcopy(res)
            # update res_to_add
            # for each reactant in res_to_add, check if it is the one to be replaced
            for i, reactant in enumerate(res_to_add['reactants']):
                if reactant['smiles'] == coref_smiles_to_graphs[smiles]:
                    res_to_add['reactants'][i]['smiles'] = Chem.MolToSmiles(edit_mol)
                    res_to_add['reactants'][i]['smiles_no_map'] = Chem.MolToSmiles(edit_mol)
                    return res_to_add
    return None

def get_r_group_frags_and_substitute(other_prod_mol, query, reactant_mols, reactant_information, parsed, toreturn):
    """
    other_prod_mol: mol object of the product to get r-groups from
    query: smiles string of product with r-groups
    reactant_mols: list of reactant mol objects to be substituted
    reactant_information: list of dictionaries of reactant information
    parsed: dictionary containing information of how r-groups in query are supposed to be substituted
    toreturn: list of reactions to be returned
    """
    query_mol = Chem.MolFromSmiles(query)
    
    # get r-group sites in query
    query_r_sites = get_sites(query_mol, '[*]', True)
    query_r_sites_reversed = {}
    for i in range(len(query_r_sites)):
        query_r_sites_reversed[query_r_sites[i][0]] = i
    
    # get r-group labels in query
    query_r_labels = {}
    for atom in query_mol.GetAtoms():
        if atom.GetAtomicNum() == 0:
            query_r_labels[atom.GetIdx()] = atom.GetProp('dummyLabel')

    # get mapping of other_prod_mol to query
    other_prod_to_query_list, query_to_other_prod_list, other_prod_mol, _ = get_atom_mapping(other_prod_mol, query, query_r_sites_reversed)

    # for each possible mapping
    for other_prod_to_query, query_to_other_prod in zip(other_prod_to_query_list, query_to_other_prod_list):
        # get r-group fragments
        r_group_frags = {}
        for atom in other_prod_mol.GetAtoms():
            if atom.GetIdx() in other_prod_to_query.keys():
                continue
            # if atom is not in query, it is part of an r-group
            # get neighbors of atom
            for neighbor in atom.GetNeighbors():
                # if neighbor is in query, then this is the attachment point
                if neighbor.GetIdx() in other_prod_to_query.keys():
                    # get r-group label in query
                    query_idx = other_prod_to_query[neighbor.GetIdx()]
                    r_label = query_r_labels[query_idx]
                    
                    # get fragment
                    q = [atom.GetIdx()]
                    seen = set(q)
                    head = 0
                    while head < len(q):
                        cur = q[head]
                        head += 1
                        for n in other_prod_mol.GetAtomWithIdx(cur).GetNeighbors():
                            if n.GetIdx() not in seen and n.GetIdx() not in other_prod_to_query.keys():
                                q.append(n.GetIdx())
                                seen.add(n.GetIdx())
                    frag = Chem.PathToSubmol(other_prod_mol, q)
                    frag = Chem.MolToSmiles(frag)
                    r_group_frags[r_label] = frag
        
        # substitute r-groups into reactants
        new_reactants = []
        for i in range(len(reactant_mols)):
            reactant_mol = reactant_mols[i]
            reactant_info = reactant_information[i]
            if reactant_info['smiles'] in parsed.keys():
                to_sub = parsed[reactant_info['smiles']]
                new_mol = Chem.MolFromSmiles(to_sub)
                
                for r_label, frag in r_group_frags.items():
                    patt = Chem.MolFromSmiles(f'[*:{r_label}]')
                    if new_mol.HasSubstructMatch(patt):
                        frag_mol = Chem.MolFromSmiles(frag)
                        new_mol = Chem.ReplaceSubstructs(new_mol, patt, frag_mol)[0]
                new_reactants.append(Chem.MolToSmiles(new_mol))
            else:
                new_reactants.append(reactant_info['smiles'])
    
        # add to toreturn
        final_reactants = []
        for i in range(len(new_reactants)):
            final_reactants.append({
                'smiles': new_reactants[i],
                'smiles_no_map': new_reactants[i]
            })
        toreturn.append({
            'reactants': final_reactants,
            'products': [{'smiles': Chem.MolToSmiles(other_prod_mol), 'smiles_no_map': Chem.MolToSmiles(other_prod_mol)}],
        })

    return

def query_enumeration(prod_template_mol_query, r_sites_reversed_new, num_r_groups):
    # returns a dictionary of r-group combinations to queries
    subsets = generate_subsets(num_r_groups)
    results = {}
    for subset in subsets:
        query = Chem.RWMol(prod_template_mol_query)
        r_group_indices = []
        for i in range(num_r_groups):
            if i not in subset:
                r_group_indices.append(r_sites_reversed_new[i])
        for idx in r_group_indices:
            query.GetAtomWithIdx(idx).SetAtomicNum(6) # C
            query.GetAtomWithIdx(idx).SetNoImplicit(True)

        results[subset] = Chem.MolToSmiles(query)
    return results

def generate_subsets(n):
    subsets = []
    def backtrack(start, subset):
        subsets.append(list(subset))
        for i in range(start, n):
            subset.append(i)
            backtrack(i + 1, subset)
            subset.pop()
    backtrack(0, [])
    return subsets

def backout(results, coref_results, molscribe):
    """
    for each reaction, if it contains an R-group, try to find a similar reaction that does not contain an R-group and "back out" the R-groups
    """
    final_results = []
    # get all reactions without r-groups
    for i, res in enumerate(results):
        new_res = {'reactions': []}
        final_results.append(new_res)
        for rxn in res['reactions']:
            if 'smiles' in rxn['products'][0].keys():
                prod_smiles = rxn['products'][0]['smiles']
                if prod_smiles is not None and "*" not in prod_smiles and "R" not in prod_smiles:
                    new_res['reactions'].append(rxn)

    # get all reactions with r-groups
    for i, res in enumerate(results):
        coref_res = clean_corefs(coref_results, i)
        if coref_res is None:
            continue
        mol_bboxes_text, coref_smiles, bboxes = coref_res
        coref_smiles_to_graphs = {}
        for k, v in coref_smiles.items():
            for text, smiles in mol_bboxes_text:
                if v == text:
                    coref_smiles_to_graphs[smiles] = k
        for rxn in res['reactions']:
            if 'smiles' in rxn['products'][0].keys():
                prod_smiles = rxn['products'][0]['smiles']
                if prod_smiles is not None and "*" in prod_smiles:
                    # this is a reaction with r-groups
                    # find a similar reaction without r-groups
                    for other_res in results:
                        for other_rxn in other_res['reactions']:
                            if 'smiles' in other_rxn['products'][0].keys():
                                other_prod_smiles = other_rxn['products'][0]['smiles']
                                if other_prod_smiles is not None and "*" not in other_prod_smiles:
                                    # this is a reaction without r-groups
                                    # check if they are similar
                                    prod_mol = Chem.MolFromSmiles(prod_smiles.replace('*', 'C'))
                                    other_prod_mol = Chem.MolFromSmiles(other_prod_smiles)
                                    if prod_mol is not None and other_prod_mol is not None and prod_mol.HasSubstructMatch(other_prod_mol):
                                        # they are similar, so we can back out the r-groups
                                        # for each reactant, if it is in coref_smiles_to_graphs, then replace it with the corresponding smiles
                                        new_rxn = {'reactants': [], 'products': rxn['products']}
                                        for reactant in rxn['reactants']:
                                            if 'smiles' in reactant.keys() and reactant['smiles'] in coref_smiles_to_graphs.keys():
                                                new_rxn['reactants'].append({'smiles': coref_smiles_to_graphs[reactant['smiles']]})
                                            else:
                                                new_rxn['reactants'].append(reactant)
                                        new_res['reactions'].append(new_rxn)
    return final_results

    # for each product, get atom mapping
    # prod_smiles_to_mol = {}
    # for i, res in enumerate(results):
    #     for rxn in res['reactions']:
    #         if 'smiles' in rxn['products'][0].keys():
    #             prod_smiles = rxn['products'][0]['smiles']
    #             if prod_smiles not in prod_smiles_to_mol.keys():
    #                 prod_smiles_to_mol[prod_smiles] = Chem.MolFromSmiles(prod_smiles)
    # for i, res in enumerate(results):
    #     if 'reactions' not in res.keys():
    #         res['reactions'] = []
    #     coref_res = clean_corefs(coref_results, i)
    #     if coref_res is None:
    #         continue
    #     mol_bboxes_text, coref_smiles, bboxes = coref_res
    #     # for each coref, get smiles and graph
    #     coref_smiles_to_graphs = {}
    #     for k, v in coref_smiles.items():
    #         for text, smiles in mol_bboxes_text:
    #             if v == text:
    #                 coref_smiles_to_graphs[smiles] = k
        
    #     for other_res in results:
    #         for other_rxn in other_res['reactions']:
    #             if 'smiles' in other_rxn['products'][0].keys():
    #                 other_prod_smiles = other_rxn['products'][0]['smiles']
    #                 if other_prod_smiles is not None and "*" not in other_prod_smiles:
    #                     # this is a reaction without r-groups
    #                     # check if it is similar to any of the coref molecules
    #                     for coref_smiles, graph in coref_smiles_to_graphs.items():
    #                         # print(coref_smiles, other_prod_smiles)
    #                         if coref_smiles is not None and Chem.MolFromSmiles(coref_smiles).HasSubstructMatch(Chem.MolFromSmiles(other_prod_smiles)):
    #                             # they are similar, so we can replace the coref with the other product
    #                             # and add this as a new reaction
    #                             new_rxn = {'reactants': [], 'products': other_rxn['products']}
    #                             for reactant in res['reactions'][0]['reactants']:
    #                                 if 'smiles' in reactant.keys() and reactant['smiles'] == graph:
    #                                     new_rxn['reactants'].append({'smiles': other_prod_smiles})
    #                                 else:
    #                                     new_rxn['reactants'].append(reactant)
    #                             res['reactions'].append(new_rxn)

    # for i, res in enumerate(results):
    #     coref_res = clean_corefs(coref_results, i)
    #     if coref_res is None:
    #         continue
    #     mol_bboxes_text, coref_smiles, bboxes = coref_res
    #     for rxn in res['reactions']:
    #         if 'smiles' not in rxn['products'][0].keys() or rxn['products'][0]['smiles'] is None:
    #             continue
    #         if "*" in rxn['products'][0]['smiles']:
    #             continue
    #         prod_smiles = rxn['products'][0]['smiles']
    #         prod_mol = prod_smiles_to_mol[prod_smiles]
    #         for other_prod_smiles, other_prod_mol in prod_smiles_to_mol.items():
    #             if "*" not in other_prod_smiles:
    #                 continue
    #             if other_prod_mol is None:
    #                 continue
    #             prod_template_mol = Chem.MolFromSmiles(other_prod_smiles.replace('*', 'C'))
    #             if prod_template_mol is not None and prod_mol.HasSubstructMatch(prod_template_mol):
    #                 # they are similar, so we can back out the r-groups
    #                 # find reaction with other_prod_smiles as product
    #                 for other_res in results:
    #                     for other_rxn in other_res['reactions']:
    #                         if 'smiles' in other_rxn['products'][0].keys() and other_rxn['products'][0]['smiles'] == other_prod_smiles:
    #                             # found the reaction with r-groups
    #                             # get r-group fragments
    #                             get_r_group_frags_and_substitute(prod_mol, other_prod_smiles, [prod_smiles_to_mol[r['smiles']] for r in other_rxn['reactants']], other_rxn['reactants'], coref_smiles, res['reactions'])
    # return results


def associate_corefs(results, results_coref):
    # for each reaction, check if there are coreferences
    # if so, add the coreferences to the reaction
    for i, res in enumerate(results):
        coref_res = clean_corefs(results_coref, i)
        if coref_res is None:
            continue
        mol_bboxes_text, coref_smiles, bboxes = coref_res
        for rxn in res['reactions']:
            if 'smiles' not in rxn['products'][0].keys() or rxn['products'][0]['smiles'] is None:
                continue
            prod_smiles = rxn['products'][0]['smiles']
            if "*" in prod_smiles:
                # this is a reaction with r-groups
                # get r-group labels
                prod_mol = Chem.MolFromSmiles(prod_smiles)
                r_labels = []
                for atom in prod_mol.GetAtoms():
                    if atom.GetAtomicNum() == 0:
                        r_labels.append(atom.GetProp('dummyLabel'))
                
                # for each r-group, find its smiles from coref
                r_group_smiles = {}
                for r_label in r_labels:
                    if r_label in coref_smiles.keys():
                        r_group_smiles[r_label] = coref_smiles[r_label]
                
                # expand reaction
                new_rxn = {'reactants': rxn['reactants'], 'products': rxn['products']}
                for r_label, smiles in r_group_smiles.items():
                    for reactant in new_rxn['reactants']:
                        if 'smiles' in reactant.keys() and reactant['smiles'] == f'[{r_label}]':
                            reactant['smiles'] = smiles
                res['reactions'].append(new_rxn)

    return results

def expand_reactions_with_backout(initial_results, results_coref, molscribe): 
    # for each reaction with R-groups, find a corresponding reaction without R-groups in the same figure
    # if found, use that as a template to expand the R-group reaction
    results = copy.deepcopy(initial_results)
    for i, res in enumerate(results):
        res['reactions_to_add'] = []
        coref_res = clean_corefs(results_coref, i)
        if coref_res is None:
            continue
        mol_bboxes_text, coref_smiles, bboxes = coref_res
        
        # for each reaction with r-groups
        for rxn in res['reactions']:
            if 'smiles' in rxn['products'][0].keys() and rxn['products'][0]['smiles'] is not None and "*" in rxn['products'][0]['smiles']:
                prod_smiles_with_r = rxn['products'][0]['smiles']
                prod_mol_with_r = Chem.MolFromSmiles(prod_smiles_with_r)
                if prod_mol_with_r is None:
                    continue
                # find a similar reaction without r-groups
                for other_rxn in res['reactions']:
                    if 'smiles' in other_rxn['products'][0].keys() and other_rxn['products'][0]['smiles'] is not None and "*" not in other_rxn['products'][0]['smiles']:
                        prod_smiles_no_r = other_rxn['products'][0]['smiles']
                        prod_mol_no_r = Chem.MolFromSmiles(prod_smiles_no_r)
                        if prod_mol_no_r is None:
                            continue
                        
                        prod_mol_with_r_no_r = Chem.MolFromSmiles(prod_smiles_with_r.replace('*', 'C'))
                        if prod_mol_no_r.HasSubstructMatch(prod_mol_with_r_no_r):
                            # similar reaction found
                            # expand r-groups
                            new_rxn = expand_r_group_label_helper(other_rxn, coref_smiles, (None, prod_smiles_no_r), molscribe)
                            if new_rxn is not None:
                                res['reactions_to_add'].append(new_rxn)
    for res in results:
        res['reactions'].extend(res['reactions_to_add'])
        del res['reactions_to_add']
    return results