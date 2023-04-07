import codecs
import jieba
import numpy as np
from algorithm import isolation_forest
from algorithm import data_processing
from algorithm import average_value
import torch
import time
import pandas as pd
from tqdm import tqdm

# 添加自定义词
def add_custom_words():
    custom_words = ["天猫", "天天特买工厂店", "自营店", "奢侈品", "正品代购"]
    for word in custom_words:
        jieba.add_word(word)

# 读取文件
def read_file(file_path):
    result = []
    with codecs.open(file_path, 'rb', 'gb18030', errors='ignore') as csvfile:
        for line in csvfile:
            temp1 = line.split('\t')
            result.append(temp1)
    return result


def get_product_category(data):
    category_dict = {}
    product_lists = []

    for i, row in enumerate(data):
        if i == 0:
            continue

        product_title = jieba.lcut(row[-1])
        product_desc = jieba.lcut(row[2])

        # Skip rows containing specific keywords
        skip_words1 = ["旗舰店", "天天特卖工厂店", "天猫", "自营店"]
        skip_words2 = ["正品代购", "奢侈品", "闲鱼"]
        if any(word in product_title for word in skip_words1) or any(word in product_desc for word in skip_words2):
            continue

        # Fill missing inventory value
        if row[15] == '':
            row[15] = row[6]

        # Find the highest level category
        category_index = next((index for index in range(12, 7, -1) if row[index] != ''), 8)
        category = jieba.lcut(row[category_index])
        row[12] = category[0] if '/' in category else row[category_index]

        if row[12] not in category_dict:
            category_dict[row[12]] = len(product_lists)
            product_lists.append([])

        product_lists[category_dict[row[12]]].append(row)

    return category_dict, product_lists


def detect_anomalies(data_dict, product_lists, update_callback=None):
    anomaly_count = 0
    anomaly_results = []
    total_products = sum(len(products) for products in product_lists)
    processed_products = 0

    for i, (category, products) in enumerate(zip(data_dict.keys(), product_lists)):
        print(f"Processing category {i + 1}/{len(data_dict)}: {category}")  # 添加日志
        price_glsf = isolation_forest(data_processing(products, 5))
        sales_glsf = isolation_forest(data_processing(products, 6))
        inventory_sales = [1 if float(row[6]) <= float(row[15]) else -1 for row in products]
        price_below_avg = [1 if average_value(products, 5) > float(row[5]) else -1 for row in products]

        for i, (price_anomaly, sales_anomaly, inventory_anomaly, price_avg_anomaly) in enumerate(
                zip(price_glsf, sales_glsf, inventory_sales, price_below_avg)):
            anomaly_type = ""

            if (price_anomaly == -1 and price_avg_anomaly == -1) or (
                    price_anomaly == -1 and inventory_anomaly == -1) or (
                    price_avg_anomaly == -1 and inventory_anomaly == -1):
                anomaly_type = "价格异常"

            if sales_anomaly == -1:
                anomaly_type = "销量异常" if not anomaly_type else anomaly_type + "+销量异常"

            if anomaly_type:
                anomaly_count += 1
                anomaly_results.append((products[i][1], anomaly_type))
            processed_products += 1
            if update_callback is not None:
                update_callback(processed_products * 100 // total_products)
    return anomaly_count, anomaly_results, total_products

def save_result(anomaly_count, anomaly_results, file_path):
    data = {
        "异常商品": [item[0] for item in anomaly_results],
        "异常类型": [item[1] for item in anomaly_results]
    }

    df = pd.DataFrame(data)
    df.loc[len(df.index)] = ['异常商品数量', anomaly_count]
    df.to_excel(file_path, index=False)

    # Save as HTML
    html_file_path = file_path.replace('.xlsx', '.html')
    df.to_html(html_file_path, index=False)

progress = 0

def update_progress(new_progress):
    global progress
    progress = new_progress

def get_progress():
    global progress
    return progress

def analyze_abnormal_products(input_file_path,output_file_path,update_callback=None):
    input_file_path = input_file_path
    output_file_path = output_file_path

    start_time = time.time()

    add_custom_words()
    data = read_file(input_file_path)
    data_dict, product_lists = get_product_category(data)
    anomaly_count, anomaly_results, total_products = detect_anomalies(data_dict, product_lists, update_callback=update_callback)
    save_result(anomaly_count, anomaly_results, output_file_path)

    end_time = time.time()
    running_time = end_time - start_time

    print("Anomaly detection completed.")
    print(f"Total anomalies detected: {anomaly_count}")
    print(f"Results saved to: {output_file_path}")
    print(f"Running time: {running_time:.2f} seconds")
    return anomaly_count, total_products  # 将 anomaly_count 作为返回值

if __name__ == "__main__":
    analyze_abnormal_products("test.tsv", "test1.xlsx")

