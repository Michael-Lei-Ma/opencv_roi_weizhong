# -*- coding: utf-8 -*-
import os
import yaml


def read_all_yaml_files(directory_path):
    """
    读取指定目录下所有.yaml文件的内容，并合并到一个字典中

    Args:
        directory_path (str): 包含.yaml文件的目录路径

    Returns:
        dict: 合并后的字典，键为文件名（不含扩展名），值为yaml内容
    """
    all_yaml_content = {}

    # 检查目录是否存在
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"目录不存在: {directory_path}")

    # 遍历目录中的所有文件
    for filename in os.listdir(directory_path):
        # 检查文件扩展名是否为.yaml或.yml
        if filename.lower().endswith(('.yaml', '.yml')):
            file_path = os.path.join(directory_path, filename)

            # 读取并解析YAML文件
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    yaml_content = yaml.safe_load(file)

                    # 使用文件名（不含扩展名）作为键
                    key_name = os.path.splitext(filename)[0]
                    all_yaml_content[key_name] = yaml_content

                    print(f"成功读取: {filename}")
            except yaml.YAMLError as e:
                print(f"YAML解析错误 {filename}: {e}")
            except Exception as e:
                print(f"读取文件错误 {filename}: {e}")

    return all_yaml_content


# 示例用法
if __name__ == "__main__":
    # 替换为实际的目录路径
    # folder_path = "folds"  # 或者使用绝对路径如 "/path/to/your/folds"
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
    os.makedirs(folder_path, exist_ok=True)
    try:
        result_dict = read_all_yaml_files(folder_path)

        # 打印结果
        for key, value in result_dict.items():
            # print(f"\n--- {key} ---")
            # print(yaml.dump(value, default_flow_style=False, allow_unicode=True))
            print(f"{key}: {value}")

        print(f"\n总共读取了 {len(result_dict)} 个YAML文件")

    except FileNotFoundError as e:
        print(e)