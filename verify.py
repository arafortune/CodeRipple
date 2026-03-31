#!/usr/bin/env python3
"""
验证脚本 - 测试基本功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    print("测试导入...")
    try:
        from src.config import Config
        from src.git.repo import GitRepository
        from src.core.tracer import BugTracer
        from src.core.result import TraceResult
        from src.core.strategies.commit_chain import CommitChainStrategy
        from src.core.strategies.code_block import CodeBlockStrategy
        from src.core.strategies.ast_structure import ASTStructureStrategy
        from src.core.strategies.similarity import SimilarityStrategy
        from src.parser.ast import ASTParser
        from src.parser.normalizer import ASTNormalizer
        from src.parser.features import FeatureExtractor
        from src.parser.similarity import SimilarityCalculator
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("\n测试配置...")
    try:
        from src.config import Config
        config = Config.default()
        assert config.get_similarity_threshold() == 0.85
        print("✓ 配置测试通过")
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def test_result():
    """测试结果"""
    print("\n测试结果...")
    try:
        from src.core.result import TraceResult
        result = TraceResult.not_found()
        assert result.found is False
        assert result.confidence == 0.0
        print("✓ 结果测试通过")
        return True
    except Exception as e:
        print(f"✗ 结果测试失败: {e}")
        return False

def test_parser():
    """测试解析器"""
    print("\n测试解析器...")
    try:
        from src.parser.ast import ASTParser
        from src.parser.normalizer import ASTNormalizer
        from src.parser.features import FeatureExtractor
        
        parser = ASTParser('python')
        ast = parser.parse("def func(): return 1")
        assert ast is not None
        
        normalizer = ASTNormalizer()
        normalized = normalizer.normalize(ast)
        assert normalized.fingerprint is not None
        
        extractor = FeatureExtractor('python')
        features = extractor.extract("def func(): return 1")
        assert len(features.tokens) > 0
        
        print("✓ 解析器测试通过")
        return True
    except Exception as e:
        print(f"✗ 解析器测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("CodeRipple 验证脚本")
    print("=" * 50)
    
    results = []
    results.append(test_imports())
    results.append(test_config())
    results.append(test_result())
    results.append(test_parser())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✓ 所有测试通过")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())
