#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE 化学信息提取工具
支持从PDF和图片中提取分子、反应、图表等化学信息
"""

import torch
from openchemie import OpenChemIE
import os
import json
import argparse
import cv2
import glob
from datetime import datetime
from pathlib import Path
import sys


class OpenChemIEExtractor:
    def __init__(self, device=None, verbose=True):
        """
        初始化提取器
        
        Args:
            device: 计算设备 ('cuda', 'cpu' 或 None 自动选择)
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        
        # 设置设备
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        if self.verbose:
            print(f"使用设备: {self.device}")
        
        # 初始化模型
        try:
            self.model = OpenChemIE(device=self.device)
            if self.verbose:
                print("OpenChemIE模型初始化成功")
        except Exception as e:
            raise RuntimeError(f"模型初始化失败: {e}")
    
    def extract_from_pdf(self, pdf_path, output_images=False, output_bbox=True, extract_corefs=True):
        """
        从PDF文件中提取所有化学信息
        
        Args:
            pdf_path: PDF文件路径
            output_images: 是否输出图片
            output_bbox: 是否输出边界框信息
            extract_corefs: 是否提取分子共指关系
            
        Returns:
            dict: 包含所有提取信息的字典
        """
        results = {
            "file_path": pdf_path,
            "file_type": "pdf",
            "timestamp": datetime.now().isoformat(),
            "extraction_config": {
                "output_images": output_images,
                "output_bbox": output_bbox,
                "extract_corefs": extract_corefs,
                "device": str(self.device)
            },
            "molecules": {
                "from_figures": [],
                "from_text": []
            },
            "reactions": {
                "from_figures": []
            },
            "figures": [],
            "tables": [],
            "coreferences": [],  # 新增：分子共指关系
            "statistics": {
                "total_molecules": 0,
                "total_reactions": 0,
                "total_figures": 0,
                "total_tables": 0,
                "total_corefs": 0,  # 新增
                "pages_processed": 0
            },
            "errors": []
        }
        
        if not os.path.exists(pdf_path):
            error_msg = f"PDF文件不存在: {pdf_path}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
            return results
        
        if self.verbose:
            print(f"开始处理PDF: {pdf_path}")
        
        # 1. 提取图片中的分子
        if self.verbose:
            print("提取图片中的分子...")
        try:
            molecule_results = self.model.extract_molecules_from_figures_in_pdf(pdf_path)
            
            for i, result in enumerate(molecule_results):
                figure_data = {
                    "figure_id": i + 1,
                    "page": result['page'],
                    "molecule_count": len(result['molecules']),
                    "molecules": []
                }
                
                for j, mol in enumerate(result['molecules']):
                    mol_data = {
                        "molecule_id": j + 1,
                        "smiles": mol['smiles'],
                        "confidence": mol.get('confidence', None),
                        "bbox": mol.get('bbox', None) if output_bbox else None,
                        "molfile": mol.get('molfile', None),  # 新增：分子文件
                        "score": mol.get('score', None)  # 新增：置信分数
                    }
                    figure_data["molecules"].append(mol_data)
                    results["statistics"]["total_molecules"] += 1
                
                results["molecules"]["from_figures"].append(figure_data)
            
            if self.verbose:
                print(f"从图片中提取到 {results['statistics']['total_molecules']} 个分子")
                
        except Exception as e:
            error_msg = f"提取图片分子时出错: {str(e)}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
        
        # 2. 提取文本中的分子
        if self.verbose:
            print("提取文本中的分子...")
        try:
            text_results = self.model.extract_molecules_from_text_in_pdf(pdf_path)
            
            for page_result in text_results:
                page_data = {
                    "page": page_result['page'],
                    "segments": []
                }
                
                for segment in page_result['molecules']:
                    segment_data = {
                        "text": segment.get('text', ''),
                        "entities": segment.get('entities', []),
                        "labels": segment.get('labels', []),  # 新增：标签信息
                        "bbox": segment.get('bbox', None) if output_bbox else None
                    }
                    page_data["segments"].append(segment_data)
                
                results["molecules"]["from_text"].append(page_data)
                results["statistics"]["pages_processed"] = max(
                    results["statistics"]["pages_processed"], 
                    page_result['page'] + 1
                )
            
            if self.verbose:
                print(f"处理了 {len(text_results)} 页文本")
                
        except Exception as e:
            error_msg = f"提取文本分子时出错: {str(e)}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
        
        # 3. 提取反应
        if self.verbose:
            print("提取化学反应...")
        try:
            reaction_results = self.model.extract_reactions_from_figures_in_pdf(pdf_path)
            
            for i, result in enumerate(reaction_results):
                figure_data = {
                    "figure_id": i + 1,
                    "page": result['page'],
                    "reaction_count": len(result['reactions']),
                    "reactions": []
                }
                
                for j, rxn in enumerate(result['reactions']):
                    rxn_data = {
                        "reaction_id": j + 1,
                        "reaction_smiles": rxn.get('reaction_smiles', ''),
                        "reactants": rxn.get('reactants', []),
                        "products": rxn.get('products', []),
                        "conditions": rxn.get('conditions', {}),
                        "confidence": rxn.get('confidence', None),
                        "bbox": rxn.get('bbox', None) if output_bbox else None
                    }
                    figure_data["reactions"].append(rxn_data)
                    results["statistics"]["total_reactions"] += 1
                
                results["reactions"]["from_figures"].append(figure_data)
            
            if self.verbose:
                print(f"提取到 {results['statistics']['total_reactions']} 个反应")
                
        except Exception as e:
            error_msg = f"提取反应时出错: {str(e)}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
        
        # 4. 提取分子共指关系
        if extract_corefs:
            if self.verbose:
                print("提取分子共指关系...")
            try:
                coref_results = self.model.extract_molecule_corefs_from_figures_in_pdf(pdf_path)
                
                for i, coref_result in enumerate(coref_results):
                    coref_data = {
                        "figure_id": i + 1,
                        "page": coref_result['page'],
                        "bboxes": []
                    }
                    
                    # 处理边界框信息
                    for bbox in coref_result.get('bboxes', []):
                        bbox_data = {
                            "category": bbox.get('category', ''),
                            "bbox": bbox.get('bbox', None) if output_bbox else None,
                            "category_id": bbox.get('category_id', None),
                            "score": bbox.get('score', None),
                            "smiles": bbox.get('smiles', ''),
                            "text": bbox.get('text', [])
                        }
                        coref_data["bboxes"].append(bbox_data)
                    
                    # 处理共指关系对
                    coref_data["coreference_pairs"] = coref_result.get('corefs', [])
                    coref_data["total_pairs"] = len(coref_result.get('corefs', []))
                    
                    results["coreferences"].append(coref_data)
                    results["statistics"]["total_corefs"] += len(coref_result.get('corefs', []))
                
                if self.verbose:
                    print(f"提取到 {results['statistics']['total_corefs']} 个共指关系对")
                    
            except Exception as e:
                error_msg = f"提取分子共指关系时出错: {str(e)}"
                results["errors"].append(error_msg)
                if self.verbose:
                    print(f"错误: {error_msg}")
        
        # 5. 提取图表
        if self.verbose:
            print("提取图表信息...")
        try:
            figures = self.model.extract_figures_from_pdf(
                pdf_path, 
                output_bbox=output_bbox, 
                output_image=output_images
            )
            tables = self.model.extract_tables_from_pdf(
                pdf_path, 
                output_bbox=output_bbox, 
                output_image=output_images
            )
            
            # 处理图片
            for i, fig in enumerate(figures):
                figure_data = {
                    "figure_id": i + 1,
                    "page": fig.get('page', 'unknown'),
                    "title": self._extract_text_from_title(fig.get('title', {})),
                    "caption": self._extract_text_from_caption(fig.get('footnote', {})),
                    "bbox": fig.get('figure', {}).get('bbox', None) if output_bbox else None,
                    "image_path": None
                }
                
                # 处理图片文件
                if output_images and fig.get('figure', {}).get('image'):
                    try:
                        image_filename = f"figure_{fig.get('page', 0)}_{i+1}.png"
                        fig['figure']['image'].save(image_filename)
                        figure_data["image_path"] = image_filename
                    except Exception as e:
                        if self.verbose:
                            print(f"保存图片失败: {e}")
                
                results["figures"].append(figure_data)
            
            # 处理表格 - 改进表格内容提取
            for i, table in enumerate(tables):
                table_data = {
                    "table_id": i + 1,
                    "page": table.get('page', 'unknown'),
                    "title": self._extract_text_from_title(table.get('title', {})),
                    "caption": self._extract_text_from_caption(table.get('footnote', {})),
                    "bbox": table.get('table', {}).get('bbox', None) if output_bbox else None,
                    "content": self._process_table_content(table.get('table', {}).get('content', None))
                }
                results["tables"].append(table_data)
            
            results["statistics"]["total_figures"] = len(figures)
            results["statistics"]["total_tables"] = len(tables)
            
            if self.verbose:
                print(f"提取到 {len(figures)} 个图片，{len(tables)} 个表格")
                
        except Exception as e:
            error_msg = f"提取图表时出错: {str(e)}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
        
        return results
    
    def _extract_text_from_title(self, title_data):
        """从标题数据中提取文本"""
        if isinstance(title_data, dict):
            return title_data.get('text', '')
        elif isinstance(title_data, str):
            return title_data
        else:
            return ''
    
    def _extract_text_from_caption(self, caption_data):
        """从标题数据中提取文本"""
        if isinstance(caption_data, dict):
            return caption_data.get('text', '')
        elif isinstance(caption_data, str):
            return caption_data
        else:
            return ''
    
    def _process_table_content(self, content):
        """处理表格内容，确保正确提取"""
        if content is None:
            return None
        
        processed_content = {
            "columns": [],
            "rows": [],
            "column_count": 0,
            "row_count": 0
        }
        
        # 处理列头
        if 'columns' in content:
            for col in content['columns']:
                if isinstance(col, dict):
                    col_data = {
                        "text": col.get('text', ''),
                        "tag": col.get('tag', 'unknown'),
                        "bbox": col.get('bbox', None)
                    }
                else:
                    col_data = {
                        "text": str(col),
                        "tag": 'unknown',
                        "bbox": None
                    }
                processed_content["columns"].append(col_data)
            processed_content["column_count"] = len(processed_content["columns"])
        
        # 处理行数据
        if 'rows' in content:
            for row in content['rows']:
                processed_row = []
                if isinstance(row, list):
                    for cell in row:
                        if isinstance(cell, dict):
                            cell_data = {
                                "text": cell.get('text', ''),
                                "bbox": cell.get('bbox', None)
                            }
                        else:
                            cell_data = {
                                "text": str(cell),
                                "bbox": None
                            }
                        processed_row.append(cell_data)
                else:
                    # 如果行不是列表，直接处理为单个单元格
                    processed_row.append({
                        "text": str(row),
                        "bbox": None
                    })
                processed_content["rows"].append(processed_row)
            processed_content["row_count"] = len(processed_content["rows"])
        
        return processed_content
    
    def extract_from_images(self, image_paths, extract_corefs=True):
        """
        从图片文件中提取化学信息
        
        Args:
            image_paths: 图片文件路径列表
            extract_corefs: 是否提取分子共指关系
            
        Returns:
            dict: 包含所有提取信息的字典
        """
        results = {
            "file_type": "images",
            "timestamp": datetime.now().isoformat(),
            "extraction_config": {
                "device": str(self.device),
                "extract_corefs": extract_corefs
            },
            "images": [],
            "coreferences": [],  # 新增
            "statistics": {
                "total_molecules": 0,
                "total_reactions": 0,
                "total_corefs": 0,  # 新增
                "images_processed": 0
            },
            "errors": []
        }
        
        # 加载和处理图片
        images = []
        valid_paths = []
        
        for img_path in image_paths:
            if not os.path.exists(img_path):
                error_msg = f"图片文件不存在: {img_path}"
                results["errors"].append(error_msg)
                if self.verbose:
                    print(f"错误: {error_msg}")
                continue
            
            try:
                img = cv2.imread(img_path)
                if img is not None:
                    images.append(img)
                    valid_paths.append(img_path)
                    if self.verbose:
                        print(f"成功加载图片: {img_path}")
                else:
                    error_msg = f"无法读取图片: {img_path}"
                    results["errors"].append(error_msg)
                    if self.verbose:
                        print(f"错误: {error_msg}")
            except Exception as e:
                error_msg = f"加载图片 {img_path} 时出错: {str(e)}"
                results["errors"].append(error_msg)
                if self.verbose:
                    print(f"错误: {error_msg}")
        
        if not images:
            if self.verbose:
                print("没有有效的图片可以处理")
            return results
        
        # 提取分子
        if self.verbose:
            print(f"从 {len(images)} 张图片中提取分子...")
        try:
            molecule_results = self.model.extract_molecules_from_figures(images)
            
            for i, result in enumerate(molecule_results):
                image_data = {
                    "image_id": i + 1,
                    "image_path": valid_paths[i] if i < len(valid_paths) else f"image_{i+1}",
                    "molecule_count": len(result['molecules']),
                    "molecules": []
                }
                
                for j, mol in enumerate(result['molecules']):
                    mol_data = {
                        "molecule_id": j + 1,
                        "smiles": mol['smiles'],
                        "confidence": mol.get('confidence', None),
                        "bbox": mol.get('bbox', None),
                        "molfile": mol.get('molfile', None),
                        "score": mol.get('score', None)
                    }
                    image_data["molecules"].append(mol_data)
                    results["statistics"]["total_molecules"] += 1
                
                results["images"].append(image_data)
                results["statistics"]["images_processed"] += 1
            
            if self.verbose:
                print(f"提取到 {results['statistics']['total_molecules']} 个分子")
                
        except Exception as e:
            error_msg = f"提取分子时出错: {str(e)}"
            results["errors"].append(error_msg)
            if self.verbose:
                print(f"错误: {error_msg}")
        
        # 提取分子共指关系
        if extract_corefs:
            if self.verbose:
                print("提取分子共指关系...")
            try:
                coref_results = self.model.extract_molecule_corefs_from_figures(images)
                
                for i, coref_result in enumerate(coref_results):
                    coref_data = {
                        "image_id": i + 1,
                        "image_path": valid_paths[i] if i < len(valid_paths) else f"image_{i+1}",
                        "bboxes": []
                    }
                    
                    # 处理边界框信息
                    for bbox in coref_result.get('bboxes', []):
                        bbox_data = {
                            "category": bbox.get('category', ''),
                            "bbox": bbox.get('bbox', None),
                            "category_id": bbox.get('category_id', None),
                            "score": bbox.get('score', None),
                            "smiles": bbox.get('smiles', ''),
                            "text": bbox.get('text', [])
                        }
                        coref_data["bboxes"].append(bbox_data)
                    
                    # 处理共指关系对
                    coref_data["coreference_pairs"] = coref_result.get('corefs', [])
                    coref_data["total_pairs"] = len(coref_result.get('corefs', []))
                    
                    results["coreferences"].append(coref_data)
                    results["statistics"]["total_corefs"] += len(coref_result.get('corefs', []))
                
                if self.verbose:
                    print(f"提取到 {results['statistics']['total_corefs']} 个共指关系对")
                    
            except Exception as e:
                error_msg = f"提取分子共指关系时出错: {str(e)}"
                results["errors"].append(error_msg)
                if self.verbose:
                    print(f"错误: {error_msg}")
        
        return results
    
    def batch_process(self, input_dir, output_dir=None, file_pattern="*.pdf", extract_corefs=True):
        """
        批量处理文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录（如果为None，则使用输入目录）
            file_pattern: 文件匹配模式
            extract_corefs: 是否提取分子共指关系
            
        Returns:
            list: 处理结果列表
        """
        if output_dir is None:
            output_dir = input_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 查找匹配的文件
        search_pattern = os.path.join(input_dir, file_pattern)
        files = glob.glob(search_pattern)
        
        if not files:
            if self.verbose:
                print(f"在 {input_dir} 中没有找到匹配 {file_pattern} 的文件")
            return []
        
        results = []
        
        for file_path in files:
            if self.verbose:
                print(f"\n处理文件: {file_path}")
            
            # 根据文件类型选择处理方法
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                result = self.extract_from_pdf(file_path, extract_corefs=extract_corefs)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                result = self.extract_from_images([file_path], extract_corefs=extract_corefs)
            else:
                if self.verbose:
                    print(f"跳过不支持的文件类型: {file_ext}")
                continue
            
            # 保存结果
            output_file = os.path.join(
                output_dir, 
                f"{Path(file_path).stem}_results.json"
            )
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                if self.verbose:
                    print(f"结果已保存到: {output_file}")
                
                results.append({
                    "input_file": file_path,
                    "output_file": output_file,
                    "result": result
                })
                
            except Exception as e:
                error_msg = f"保存结果文件时出错: {str(e)}"
                if self.verbose:
                    print(f"错误: {error_msg}")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description="OpenChemIE 化学信息提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理单个PDF文件
  python openchemie_extractor.py --input file.pdf --output results.json
  
  # 处理单张图片
  python openchemie_extractor.py --input image.png --output results.json
  
  # 批量处理PDF文件
  python openchemie_extractor.py --batch-dir /path/to/pdfs --output-dir /path/to/results
  
  # 处理多张图片
  python openchemie_extractor.py --input img1.png img2.png img3.png --output results.json
        """
    )
    
    parser.add_argument(
        '--input', '-i', 
        nargs='+',
        help='输入文件路径（PDF或图片）'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出JSON文件路径'
    )
    
    parser.add_argument(
        '--batch-dir',
        help='批量处理目录'
    )
    
    parser.add_argument(
        '--output-dir',
        help='批量处理输出目录'
    )
    
    parser.add_argument(
        '--pattern',
        default='*.pdf',
        help='批量处理文件匹配模式（默认: *.pdf）'
    )
    
    parser.add_argument(
        '--device',
        choices=['cuda', 'cpu', 'auto'],
        default='auto',
        help='计算设备（默认: auto）'
    )
    
    parser.add_argument(
        '--output-images',
        action='store_true',
        help='输出提取的图片文件'
    )
    
    parser.add_argument(
        '--no-bbox',
        action='store_true',
        help='不输出边界框信息'
    )
    
    parser.add_argument(
        '--no-corefs',
        action='store_true',
        help='不提取分子共指关系'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，不显示详细信息'
    )
    
    args = parser.parse_args()
    
    # 检查参数
    if not args.input and not args.batch_dir:
        parser.error("必须指定 --input 或 --batch-dir")
    
    if args.input and args.batch_dir:
        parser.error("--input 和 --batch-dir 不能同时使用")
    
    # 设置环境变量
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # 初始化提取器
    device = None if args.device == 'auto' else args.device
    extractor = OpenChemIEExtractor(device=device, verbose=not args.quiet)
    
    try:
        if args.batch_dir:
            # 批量处理
            results = extractor.batch_process(
                args.batch_dir,
                args.output_dir,
                args.pattern,
                extract_corefs=not args.no_corefs
            )
            
            if not args.quiet:
                print(f"\n批量处理完成，共处理 {len(results)} 个文件")
        
        else:
            # 单文件或多文件处理
            input_files = args.input
            
            # 检查文件类型
            pdf_files = [f for f in input_files if f.endswith('.pdf')]
            image_files = [f for f in input_files if not f.endswith('.pdf')]
            
            if len(pdf_files) > 1:
                parser.error("只能处理一个PDF文件，多个PDF请使用批量模式")
            
            if pdf_files and image_files:
                parser.error("不能同时处理PDF和图片文件")
            
            # 处理文件
            if pdf_files:
                result = extractor.extract_from_pdf(
                    pdf_files[0],
                    output_images=args.output_images,
                    output_bbox=not args.no_bbox,
                    extract_corefs=not args.no_corefs
                )
            else:
                result = extractor.extract_from_images(
                    image_files, 
                    extract_corefs=not args.no_corefs
                )
            
            # 保存结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                if not args.quiet:
                    print(f"结果已保存到: {args.output}")
            else:
                # 输出到标准输出
                print(json.dumps(result, indent=2, ensure_ascii=False))
    
    except KeyboardInterrupt:
        print("\n处理被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 