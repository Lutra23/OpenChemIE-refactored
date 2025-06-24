#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE 化学信息提取工具 v2.0
采用优化的JSON输出结构，更清晰、更有条理
"""

import torch
from openchemie import OpenChemIE
import os
import json
import argparse
import cv2
import glob
import time
import psutil
from datetime import datetime
from pathlib import Path
import sys
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen


class OpenChemIEExtractorV2:
    def __init__(self, device=None, verbose=True):
        """
        初始化提取器 v2.0
        
        Args:
            device: 计算设备 ('cuda', 'cpu' 或 None 自动选择)
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.schema_version = "2.0.0"
        self.extractor_version = "2.0.0"
        
        # 设置设备
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        if self.verbose:
            print(f"🚀 OpenChemIE提取器 v{self.extractor_version} 初始化")
            print(f"📱 使用设备: {self.device}")
        
        # 初始化模型
        try:
            self.model = OpenChemIE(device=self.device)
            if self.verbose:
                print("✅ 模型加载成功")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

    def extract_from_pdf(self, pdf_path, output_images=False, output_bbox=True, extract_corefs=True):
        """
        从PDF文件中提取化学信息 - 新版本结构
        
        Args:
            pdf_path: PDF文件路径
            output_images: 是否输出提取的图片
            output_bbox: 是否输出边界框信息
            extract_corefs: 是否提取分子共指关系
            
        Returns:
            dict: 优化结构的提取结果
        """
        start_time = time.time()
        
        if self.verbose:
            print(f"\n🔍 开始处理PDF: {pdf_path}")
        
        # 检查文件是否存在
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
        
        # 获取文件信息
        file_info = self._get_file_info(pdf_path)
        
        # 初始化结果结构
        results = self._initialize_result_structure(pdf_path, file_info, {
            "output_images": output_images,
            "output_bbox": output_bbox,
            "extract_corefs": extract_corefs,
            "device": str(self.device)
        })
        
        try:
            # 提取分子
            if self.verbose:
                print("🧪 提取分子...")
            molecules_data = self._extract_molecules_from_pdf(pdf_path, output_bbox, output_images)
            
            # 提取反应
            if self.verbose:
                print("⚗️ 提取反应...")
            reactions_data = self._extract_reactions_from_pdf(pdf_path, output_bbox)
            
            # 提取图片
            if self.verbose:
                print("🖼️ 提取图片...")
            figures_data = self._extract_figures_from_pdf(pdf_path, output_bbox, output_images)
            
            # 提取表格
            if self.verbose:
                print("📊 提取表格...")
            tables_data = self._extract_tables_from_pdf(pdf_path, output_bbox)
            
            # 提取共指关系
            corefs_data = {}
            if extract_corefs:
                if self.verbose:
                    print("🔗 提取分子共指关系...")
                corefs_data = self._extract_coreferences_from_pdf(pdf_path)
            
            # 组装化学实体数据
            results["chemical_entities"] = self._build_chemical_entities(molecules_data, reactions_data)
            
            # 组装文档内容数据
            results["document_content"] = self._build_document_content(figures_data, tables_data)
            
            # 组装关系数据
            results["relationships"] = self._build_relationships(corefs_data, molecules_data)
            
            # 计算质量指标
            results["quality_metrics"] = self._calculate_quality_metrics(molecules_data, reactions_data, tables_data, corefs_data)
            
            # 处理完成
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 更新处理信息
            results["metadata"]["extraction_info"]["processing_time_seconds"] = round(processing_time, 2)
            results["statistics"] = self._calculate_statistics(results, processing_time)
            
            if self.verbose:
                print(f"✅ 处理完成！耗时: {processing_time:.2f}秒")
                self._print_summary(results)
            
            return results
            
        except Exception as e:
            if self.verbose:
                print(f"❌ 处理过程中出错: {e}")
            raise

    def _get_file_info(self, file_path):
        """获取文件基本信息"""
        file_stat = os.stat(file_path)
        return {
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }

    def _initialize_result_structure(self, file_path, file_info, config):
        """初始化结果结构"""
        return {
            "schema_version": self.schema_version,
            "metadata": {
                "extraction_info": {
                    "timestamp": datetime.now().isoformat(),
                    "extractor_version": self.extractor_version,
                    "device_used": config["device"],
                    "processing_time_seconds": 0
                },
                "document_info": {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_type": "pdf",
                    "file_size_mb": file_info["size_mb"],
                    "total_pages": 0,  # 将在处理过程中更新
                    "language": "auto_detected"
                },
                "extraction_config": config
            },
            "document_structure": {
                "pages": [],
                "total_figures": 0,
                "total_tables": 0,
                "total_text_blocks": 0
            },
            "chemical_entities": {},
            "document_content": {},
            "relationships": {},
            "quality_metrics": {},
            "statistics": {}
        }

    def _extract_molecules_from_pdf(self, pdf_path, output_bbox, output_images):
        """提取分子信息"""
        try:
            # 从图片中提取分子 - 修正参数名
            molecules_from_figures = self.model.extract_molecules_from_figures_in_pdf(pdf_path)
            
            # 从文本中提取分子  
            molecules_from_text = self.model.extract_molecules_from_text_in_pdf(pdf_path)
            
            return {
                "from_figures": molecules_from_figures,
                "from_text": molecules_from_text
            }
        except Exception as e:
            if self.verbose:
                print(f"⚠️ 分子提取警告: {e}")
            return {"from_figures": [], "from_text": []}

    def _extract_reactions_from_pdf(self, pdf_path, output_bbox):
        """提取反应信息"""
        try:
            # 修正参数名
            reactions = self.model.extract_reactions_from_figures_in_pdf(pdf_path)
            return reactions
        except Exception as e:
            if self.verbose:
                print(f"⚠️ 反应提取警告: {e}")
            return []

    def _extract_figures_from_pdf(self, pdf_path, output_bbox, output_images):
        """提取图片信息"""
        try:
            # 修正参数名
            figures = self.model.extract_figures_from_pdf(
                pdf_path, output_bbox=output_bbox, output_image=output_images
            )
            return figures
        except Exception as e:
            if self.verbose:
                print(f"⚠️ 图片提取警告: {e}")
            return []

    def _extract_tables_from_pdf(self, pdf_path, output_bbox):
        """提取表格信息"""
        try:
            # 修正参数名
            tables = self.model.extract_tables_from_pdf(
                pdf_path, output_bbox=output_bbox
            )
            return tables
        except Exception as e:
            if self.verbose:
                print(f"⚠️ 表格提取警告: {e}")
            return []

    def _extract_coreferences_from_pdf(self, pdf_path):
        """提取共指关系"""
        try:
            corefs = self.model.extract_molecule_corefs_from_figures_in_pdf(pdf_path)
            return corefs
        except Exception as e:
            if self.verbose:
                print(f"⚠️ 共指关系提取警告: {e}")
            return {}

    def _build_chemical_entities(self, molecules_data, reactions_data):
        """构建化学实体部分"""
        molecule_analysis = self._analyze_molecules(molecules_data)
        reaction_analysis = self._analyze_reactions(reactions_data)
        
        return {
            "molecules": {
                "total_unique_molecules": molecule_analysis["total_unique_molecules"],
                "total_mentions": molecule_analysis["total_mentions"],
                "source_distribution": molecule_analysis["source_distribution"],
                "confidence_metrics": molecule_analysis["confidence_metrics"],
                "property_summary": molecule_analysis["property_summary"],
                "molecule_list": molecule_analysis["molecule_list"]
            },
            "reactions": {
                "total_reactions": reaction_analysis["total_reactions"],
                "reaction_list": reaction_analysis["reaction_list"]
            }
        }
        
    def _analyze_molecules(self, molecules_data):
        """分析和整合分子数据"""
        all_molecules = []
        
        # 合并来自不同来源的分子
        for mol_list in molecules_data.values():
            all_molecules.extend(mol_list)
        
        # 去重并增强数据
        unique_molecules = {}
        molecule_id_counter = 1
        for mol_data in all_molecules:
            smiles = mol_data.get("smiles")
            if not smiles:
                continue
            
            if smiles not in unique_molecules:
                unique_molecules[smiles] = self._enhance_molecule_data(mol_data, f"MOL-{molecule_id_counter}")
                molecule_id_counter += 1
            else:
                # 合并提及次数和来源
                unique_molecules[smiles]["mentions"].append({
                    "source": mol_data.get("source", "unknown"),
                    "confidence": self._normalize_confidence(mol_data.get("score")),
                    "page": mol_data.get("page_number"),
                    "bbox": mol_data.get("bbox")
                })

        # 准备最终输出
        molecule_list = list(unique_molecules.values())
        source_distribution = self._organize_molecules_by_source(molecules_data)
        
        # 提取所有置信度分数
        all_confidences = [
            mention["confidence"] for mol in molecule_list for mention in mol["mentions"] if mention["confidence"] is not None
        ]
        
        # 提取所有分子量和LogP
        all_mw = [mol["properties"]["molecular_weight"] for mol in molecule_list if mol["properties"]["molecular_weight"] is not None]
        all_logp = [mol["properties"]["logP"] for mol in molecule_list if mol["properties"]["logP"] is not None]

        return {
            "total_unique_molecules": len(molecule_list),
            "total_mentions": len(all_molecules),
            "source_distribution": source_distribution,
            "confidence_metrics": self._analyze_confidence_distribution(all_confidences),
            "property_summary": {
                "molecular_weight": {
                    "average": round(np.mean(all_mw), 2) if all_mw else 0,
                    "std_dev": round(np.std(all_mw), 2) if all_mw else 0,
                    "min": min(all_mw) if all_mw else 0,
                    "max": max(all_mw) if all_mw else 0
                },
                "logP": {
                    "average": round(np.mean(all_logp), 2) if all_logp else 0,
                    "std_dev": round(np.std(all_logp), 2) if all_logp else 0,
                    "min": min(all_logp) if all_logp else 0,
                    "max": max(all_logp) if all_logp else 0
                }
            },
            "molecule_list": molecule_list
        }
        
    def _analyze_confidence_distribution(self, scores):
        """计算置信度分布"""
        if not scores:
            return {"average": 0, "std_dev": 0, "min": 0, "max": 0, "distribution_percentiles": {}}
        
        return {
            "average": round(np.mean(scores), 2),
            "std_dev": round(np.std(scores), 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "distribution_percentiles": {
                "p25": round(np.percentile(scores, 25), 2),
                "p50": round(np.percentile(scores, 50), 2),
                "p75": round(np.percentile(scores, 75), 2)
            }
        }

    def _organize_molecules_by_source(self, molecules_data):
        """按来源组织分子"""
        
        source_distribution = {}
        mol_id_counter = 1
        
        for source, mol_list in molecules_data.items():
            
            processed_mols = []
            
            for mol in mol_list:
                
                smiles = mol.get("smiles")
                if not smiles: continue
                
                # 为每个分子创建唯一的ID
                mol_id = f"MOL-{mol_id_counter}"
                mol_id_counter += 1
                
                # 标准化置信度
                confidence = self._normalize_confidence(mol.get("score"))
                
                # 提取其他信息
                page = mol.get("page_number", -1)
                bbox = mol.get("bbox")
                mol_image_b64 = mol.get("image") # 假设图片是base64编码
                
                # 创建分子对象
                mol_object = {
                    "id": mol_id,
                    "smiles": smiles,
                    "source": source,
                    "confidence": confidence,
                    "page": page,
                    "bbox": bbox,
                    "image_base64": mol_image_b64
                }
                
                processed_mols.append(mol_object)
                
            source_distribution[source] = {
                "count": len(processed_mols),
                "molecules": processed_mols
            }
            
        return source_distribution


    def _enhance_molecule_data(self, mol_data, mol_id):
        """使用RDKit计算分子属性并增强数据"""
        smiles = mol_data.get("smiles")
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        
        properties = {
            "molecular_weight": None,
            "formula": None,
            "logP": None,
            "num_h_donors": None,
            "num_h_acceptors": None,
            "num_rotatable_bonds": None
        }
        
        if mol:
            properties["molecular_weight"] = round(Descriptors.MolWt(mol), 2)
            properties["formula"] = Chem.rdMolDescriptors.CalcMolFormula(mol)
            properties["logP"] = round(Crippen.MolLogP(mol), 2)
            properties["num_h_donors"] = Descriptors.NumHDonors(mol)
            properties["num_h_acceptors"] = Descriptors.NumHAcceptors(mol)
            properties["num_rotatable_bonds"] = Descriptors.NumRotatableBonds(mol)
            
        return {
            "id": mol_id,
            "smiles": smiles,
            "iupac_name": mol_data.get("iupac_name"), # 假设模型可以提取
            "properties": properties,
            "mentions": [{
                "source": mol_data.get("source", "unknown"),
                "confidence": self._normalize_confidence(mol_data.get("score")),
                "page": mol_data.get("page_number"),
                "bbox": mol_data.get("bbox")
            }]
        }

    def _normalize_confidence(self, score):
        """将置信度分数归一化到0-1范围"""
        if score is None:
            return None
        # 假设分数已经是0-1范围，如果不是，需要调整
        return round(float(score), 3)

    def _analyze_reactions(self, reactions_data):
        """分析和格式化反应数据"""
        reaction_list = self._format_reactions(reactions_data)
        return {
            "total_reactions": len(reaction_list),
            "reaction_list": reaction_list
        }

    def _format_reactions(self, reactions_data):
        """格式化反应数据"""
        formatted_reactions = []
        reaction_id_counter = 1
        for rxn_data in reactions_data:
            rxn_id = f"RXN-{reaction_id_counter}"
            reaction_id_counter += 1
            
            # 提取参与物
            reactants = [m["smiles"] for m in rxn_data.get("reactants", []) if m.get("smiles")]
            products = [m["smiles"] for m in rxn_data.get("products", []) if m.get("smiles")]
            
            # 提取条件
            conditions_text = [c.get("text") for c in rxn_data.get("conditions", [])]
            
            formatted_reactions.append({
                "id": rxn_id,
                "reaction_smiles": f"{'.'.join(reactants)}>>{'.'.join(products)}",
                "reactants_smiles": reactants,
                "products_smiles": products,
                "conditions": conditions_text,
                "source": {
                    "page": rxn_data.get("page_number"),
                    "bbox": rxn_data.get("bbox")
                }
            })
        return formatted_reactions

    def _build_document_content(self, figures_data, tables_data):
        """构建文档内容部分"""
        formatted_figures = self._format_figures_data(figures_data)
        formatted_tables = self._format_tables_data(tables_data)
        
        return {
            "figures": formatted_figures,
            "tables": formatted_tables
        }

    def _format_figures_data(self, figures_data):
        """格式化图片数据"""
        formatted_figures = []
        figure_id_counter = 1
        
        for fig_data in figures_data:
            fig_id = f"FIG-{figure_id_counter}"
            figure_id_counter += 1
            
            # 提取标题和脚注
            caption = fig_data.get("title", {}).get("text", "")
            footnote = fig_data.get("footnote", {}).get("text", "")
            
            # 提取图片信息
            image_info = fig_data.get("figure", {})
            
            formatted_figures.append({
                "id": fig_id,
                "page": fig_data.get("page"),
                "bbox": image_info.get("bbox"),
                "caption": caption,
                "footnote": footnote,
                "image_base64": image_info.get("image") # 假设是base64
            })
            
        return formatted_figures

    def _format_tables_data(self, tables_data):
        """格式化表格数据"""
        formatted_tables = []
        table_id_counter = 1
        
        for tbl_data in tables_data:
            tbl_id = f"TBL-{table_id_counter}"
            table_id_counter += 1
            
            # 提取标题和脚注
            title = tbl_data.get("title", {}).get("text", "")
            footnote = tbl_data.get("footnote", {}).get("text", "")
            
            # 提取表格内容
            table_content = tbl_data.get("table", {})
            table_structure = {}
            table_data = []

            if "content" in table_content and table_content["content"]:
                content = table_content["content"]
                table_structure = self._format_table_structure(content)
                table_data = self._format_table_data(content)

            formatted_tables.append({
                "id": tbl_id,
                "page": tbl_data.get("page"),
                "bbox": table_content.get("bbox"),
                "title": title,
                "footnote": footnote,
                "structure": table_structure,
                "data": table_data
            })
            
        return formatted_tables

    def _format_table_structure(self, content):
        """格式化表格结构"""
        columns = content.get("columns", [])
        
        formatted_columns = []
        for i, col in enumerate(columns):
            formatted_columns.append({
                "index": i,
                "header": col.get("text", ""),
                "semantic_role": self._get_semantic_role(col.get("tag")),
                "data_type": self._classify_column_type(col.get("tag")) # 初步分类
            })
            
        return {
            "num_columns": len(formatted_columns),
            "num_rows": len(content.get("rows", [])),
            "columns": formatted_columns
        }
        
    def _classify_column_type(self, tag):
        """根据标签初步分类列数据类型"""
        numeric_tags = ["measurement", "temperature", "time", "result", "ratio"]
        if tag in numeric_tags:
            return "numeric"
        
        categorical_tags = ["substance", "alkyl group", "solvent", "catalyst"]
        if tag in categorical_tags:
            return "categorical"
            
        return "text"
        
    def _get_semantic_role(self, tag):
        """获取列的语义角色"""
        role_mapping = {
            "substance": "Reactant/Product",
            "reactant": "Reactant",
            "product": "Product",
            "catalyst": "Catalyst",
            "solvent": "Solvent",
            "temperature": "Condition-Temperature",
            "time": "Condition-Time",
            "yield": "Result-Yield",
            "ee": "Result-EnantiomericExcess",
            "ratio": "Stoichiometry"
        }
        return role_mapping.get(tag, "unknown")

    def _format_table_data(self, content):
        """格式化表格数据"""
        rows = content.get("rows", [])
        columns = content.get("columns", [])
        
        formatted_rows = []
        for row_idx, row in enumerate(rows):
            formatted_row = {}
            for col_idx, cell in enumerate(row):
                header = columns[col_idx].get("text", f"col_{col_idx}")
                cell_text = cell.get("text", "")
                
                # 分析单元格内容
                cell_type = self._classify_cell_type(cell_text)
                
                cell_data = {
                    "raw_text": cell_text,
                    "type": cell_type
                }
                
                if cell_type == "numeric":
                    cell_data["value"] = self._extract_numeric_value(cell_text)
                    cell_data["unit"] = self._extract_unit(cell_text)
                
                formatted_row[header] = cell_data
                
            formatted_rows.append(formatted_row)
            
        return formatted_rows

    def _classify_cell_type(self, text):
        """分类单元格数据类型"""
        if self._is_numeric(text):
            return "numeric"
        return "text"

    def _is_numeric(self, text):
        """判断字符串是否为数值"""
        # 匹配整数、小数、科学计数法、范围
        # 更宽松的匹配，允许结尾有单位
        numeric_pattern = re.compile(r"^[-\u2212\s]*(\d{1,3}(,\d{3})*|\d+)(\.\d*)?([eE][+-]?\d+)?.*")
        range_pattern = re.compile(r".*(\d+\s*-\s*\d+).*") # 如 "10-20"
        
        if numeric_pattern.match(text.strip()) or range_pattern.match(text.strip()):
            return True
        return False

    def _extract_numeric_value(self, text):
        """提取数值"""
        # 移除逗号分隔符
        text = text.replace(",", "")
        # 匹配浮点数或整数
        match = re.search(r"[-−\s]*\d+(\.\d*)?", text)
        return float(match.group(0).replace("−", "-")) if match else None
        
    def _extract_unit(self, text):
        """提取单位"""
        # 移除数值部分后，剩余部分作为单位
        # 这是一个简化方法，可能需要更复杂的逻辑
        numeric_part = re.search(r"[-−\s]*\d+(\.\d*)?", text)
        if numeric_part:
            return text[numeric_part.end():].strip()
        return None

    def _build_relationships(self, corefs_data, molecules_data):
        """构建关系部分"""
        formatted_corefs = self._format_coreferences(corefs_data, molecules_data)
        
        return {
            "coreferences": {
                "total_clusters": len(formatted_corefs),
                "clusters": formatted_corefs
            }
        }

    def _format_coreferences(self, corefs_data, molecules_data):
        """格式化共指关系"""
        
        # 1. 创建一个SMILES到分子ID的映射
        smiles_to_id = {}
        for source, mol_list in molecules_data.items():
            for mol in mol_list:
                smiles = mol.get("smiles")
                if smiles and smiles not in smiles_to_id:
                    # 假设分子ID在_enhance_molecule_data中已创建
                    # 这里我们需要一个方式来获取那个ID
                    # 简化：暂时只用SMILES作为键
                    pass 

        # 2. 处理共指链
        clusters = []
        cluster_id_counter = 1
        
        if not isinstance(corefs_data, dict):
            return []

        for entity, coref_chains in corefs_data.items():
            
            if not isinstance(coref_chains, list): continue

            for chain in coref_chains:
                cluster_id = f"COREF-{cluster_id_counter}"
                cluster_id_counter += 1
                
                mentions = []
                
                # 代表性提及 (通常是第一个)
                representative_smiles = chain[0].get("smiles")
                
                for mention_data in chain:
                    # 获取提及的分子ID
                    # 这里需要一个更可靠的机制来关联
                    # 暂时使用SMILES来查找
                    mention_smiles = mention_data.get("smiles")
                    
                    mentions.append({
                        "mention_id": f"MENTION-{len(mentions)+1}",
                        "molecule_smiles": mention_smiles,
                        "text_mention": mention_data.get("text"),
                        "source": {
                            "page": mention_data.get("page_number"),
                            "bbox": mention_data.get("bbox")
                        }
                    })
                
                clusters.append({
                    "cluster_id": cluster_id,
                    "representative_smiles": representative_smiles,
                    "mentions": mentions
                })
        
        return clusters

    def _calculate_quality_metrics(self, molecules_data, reactions_data, tables_data, corefs_data):
        """计算提取质量指标"""
        # 分子置信度
        mol_scores = [
            self._normalize_confidence(m.get("score")) 
            for m_list in molecules_data.values() 
            for m in m_list if m.get("score") is not None
        ]
        
        # 反应置信度 - 假设有
        rxn_scores = [
            r.get("confidence", 1.0) for r in reactions_data
        ]
        
        # 表格提取置信度 - 假设有
        tbl_scores = [
            t.get("confidence", 1.0) for t in tables_data
        ]
        
        return {
            "molecule_extraction_confidence": self._analyze_confidence_distribution(mol_scores),
            "reaction_extraction_confidence": self._analyze_confidence_distribution(rxn_scores),
            "table_extraction_confidence": self._analyze_confidence_distribution(tbl_scores),
            "completeness_score": round(np.mean([1 if mol_scores else 0, 1 if reactions_data else 0, 1 if tables_data else 0]), 2)
        }

    def _calculate_statistics(self, results, processing_time):
        """计算最终统计数据"""
        stats = {
            "total_processing_time_seconds": processing_time,
            "performance": {
                "pages_per_second": round(results["metadata"]["document_info"]["total_pages"] / processing_time, 2) if processing_time > 0 else 0,
                "cpu_usage_percent": psutil.cpu_percent(),
                "memory_usage_gb": round(psutil.virtual_memory().used / (1024**3), 2)
            },
            "counts": {
                "total_pages": results["metadata"]["document_info"]["total_pages"],
                "total_figures": results["document_structure"]["total_figures"],
                "total_tables": results["document_structure"]["total_tables"],
                "total_unique_molecules": results["chemical_entities"]["molecules"]["total_unique_molecules"],
                "total_reactions": results["chemical_entities"]["reactions"]["total_reactions"],
                "total_coref_clusters": results["relationships"]["coreferences"]["total_clusters"]
            }
        }
        return stats

    def _print_summary(self, results):
        """打印提取结果摘要"""
        print("\n" + "="*20 + " 提取摘要 " + "="*20)
        stats = results["statistics"]["counts"]
        print(f"📄 共处理 {stats['total_pages']} 页")
        print(f"🖼️ 找到 {stats['total_figures']} 个图片, 📊 {stats['total_tables']} 个表格")
        print(f"🧪 提取了 {stats['total_unique_molecules']} 个独立分子")
        print(f"⚗️ 识别了 {stats['total_reactions']} 个化学反应")
        print(f"🔗 发现了 {stats['total_coref_clusters']} 个共指链")
        print("="*55)
        
    def save_results(self, results, output_path):
        """
        将提取结果保存为JSON文件
        
        Args:
            results (dict): 提取结果
            output_path (str): 输出文件路径 (JSON)
        """
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        if self.verbose:
            print(f"💾 结果已保存至: {output_path}")

def main():
    """主函数，用于命令行操作"""
    parser = argparse.ArgumentParser(description="OpenChemIE v2.0 - 从PDF中提取化学信息")
    parser.add_argument("pdf_path", type=str, help="输入的PDF文件路径")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出的JSON文件路径")
    parser.add_argument("--no-images", action="store_true", help="不输出提取的图片")
    parser.add_argument("--no-bbox", action="store_true", help="不输出边界框信息")
    parser.add_argument("--no-corefs", action="store_true", help="不提取共指关系")
    parser.add_argument("--device", type=str, default=None, help="计算设备 (例如 'cuda:0' 或 'cpu')")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式，不打印详细信息")
    
    args = parser.parse_args()
    
    # 初始化提取器
    extractor = OpenChemIEExtractorV2(device=args.device, verbose=not args.quiet)
    
    # 提取信息
    results = extractor.extract_from_pdf(
        args.pdf_path,
        output_images=not args.no_images,
        output_bbox=not args.no_bbox,
        extract_corefs=not args.no_corefs
    )
    
    # 保存结果
    if args.output:
        output_path = args.output
    else:
        # 自动生成输出文件名
        base_name = Path(args.pdf_path).stem
        output_path = f"{base_name}_openchemie_results.json"
        
    extractor.save_results(results, output_path)

if __name__ == '__main__':
    main()
