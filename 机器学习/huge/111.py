import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns


def load_data(file_path):

    df = pd.read_csv(file_path, sep=r'\s+')  # Fix regex warning
    print("加载数据完成 Shape:", df.shape)
    return df



def preprocess_data(df):
    """预处理数据"""
    # 创建数据副本避免修改原始数据
    df = df.copy()

    print("原始列名:", df.columns.tolist())
    print("数据形状:", df.shape)

    # 1. 处理 power 列 (发动机功率)
    # 根据题目描述，power范围应该是[0, 600]，超出范围的可能是异常值
    df['power'] = pd.to_numeric(df['power'], errors='coerce')
    # 异常值处理：超出合理范围的设为NaN
    df.loc[df['power'] > 600, 'power'] = np.nan
    df.loc[df['power'] < 0, 'power'] = np.nan
    # 用中位数填充缺失值
    power_median = df['power'].median()
    df['power'] = df['power'].fillna(power_median)
    print(f"Power列处理完成，中位数填充值: {power_median}")

    # 2. 处理 kilometer 列 (行驶里程，单位万km)
    df['kilometer'] = pd.to_numeric(df['kilometer'], errors='coerce')
    # 异常值处理：里程数不应该为负数，过大的值也可能是异常
    df.loc[df['kilometer'] < 0, 'kilometer'] = np.nan
    df.loc[df['kilometer'] > 50, 'kilometer'] = np.nan  # 50万公里以上可能是异常值
    # 用中位数填充
    km_median = df['kilometer'].median()
    df['kilometer'] = df['kilometer'].fillna(km_median)
    print(f"Kilometer列处理完成，中位数填充值: {km_median}")

    # 3. 处理 regDate (注册日期) - 重要特征，不能删除
    df['regDate'] = df['regDate'].astype(str)
    # 提取注册年份 - 添加错误处理

    df['reg_year'] = pd.to_numeric(df['regDate'].str[:4], errors='coerce')
    # 处理异常年份（1990-2020合理范围）
    df.loc[(df['reg_year'] < 1990) | (df['reg_year'] > 2020), 'reg_year'] = np.nan
    df['reg_year'] = df['reg_year'].fillna(df['reg_year'].median())

    # 4. 创建汽车年龄特征 - 这是影响二手车价格的重要因素
    df['car_age'] = 2020 - df['reg_year']
    df['car_age'] = df['car_age'].clip(0, 30)  # 年龄限制在合理范围

    # 5. 创建里程年均值特征
    df['km_per_year'] = df['kilometer'] / (df['car_age'] + 1)  # +1避免除零

    # 6. 处理 notRepairedDamage 列
    # 根据数据，'-' 表示缺失，应该用众数填充而不是中位数
    df['notRepairedDamage'] = df['notRepairedDamage'].replace('-', np.nan)
    damage_mode = df['notRepairedDamage'].mode()
    if len(damage_mode) > 0:
        df['notRepairedDamage'] = df['notRepairedDamage'].fillna(damage_mode[0])
    else:
        df['notRepairedDamage'] = df['notRepairedDamage'].fillna('0.0')

    # 7. 处理分类变量的缺失值
    categorical_cols = ['model', 'brand', 'bodyType', 'fuelType', 'gearbox',
                        'notRepairedDamage', 'regionCode', 'seller']

    for col in categorical_cols:
        if col in df.columns:
            # 对于分类变量，用众数填充更合适
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
            else:
                df[col] = df[col].fillna('unknown')

    # 8. 处理v系列匿名特征的缺失值
    v_cols = [col for col in df.columns if col.startswith('v_')]
    for col in v_cols:
        if col in df.columns:
            # 数值型匿名特征用中位数填充
            df[col] = pd.to_numeric(df[col], errors='coerce')
            col_median = df[col].median()
            df[col] = df[col].fillna(col_median)

    # 9. 编码分类变量
    label_encoders = {}
    for col in categorical_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = df[col].astype(str)
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le

    # 10. 处理上线时间（creatDate）
    if 'creatDate' in df.columns:
        df['creatDate'] = df['creatDate'].astype(str)

        # 检查并清理 creatDate 数据
        print(f"creatDate 示例值: {df['creatDate'].head()}")
        print(f"creatDate 唯一值数量: {df['creatDate'].nunique()}")

        # 过滤出有效的日期格式（8位数字）
        valid_date_mask = df['creatDate'].str.len() == 8
        valid_date_mask = valid_date_mask & df['creatDate'].str.isdigit()

        # 初始化年份和月份列
        df['create_year'] = np.nan
        df['create_month'] = np.nan

        # 只对有效日期进行处理
        if valid_date_mask.any():
            try:
                df.loc[valid_date_mask, 'create_year'] = pd.to_numeric(
                    df.loc[valid_date_mask, 'creatDate'].str[:4], errors='coerce'
                )
                df.loc[valid_date_mask, 'create_month'] = pd.to_numeric(
                    df.loc[valid_date_mask, 'creatDate'].str[4:6], errors='coerce'
                )
            except Exception as e:
                print(f"处理有效日期时出错: {e}")

        # 填充缺失的年份和月份
        create_year_median = df['create_year'].median()
        create_month_median = df['create_month'].median()

        if pd.isna(create_year_median):
            create_year_median = 2016  # 默认年份
        if pd.isna(create_month_median):
            create_month_median = 6  # 默认月份

        df['create_year'] = df['create_year'].fillna(create_year_median)
        df['create_month'] = df['create_month'].fillna(create_month_median)

        # 创建上线时间特征：相对于基准时间的天数

        base_date = pd.to_datetime('20160101', format='%Y%m%d')
        # 构建有效的日期字符串
        df['date_str'] = (df['create_year'].astype(int).astype(str) +
                              df['create_month'].astype(int).astype(str).str.zfill(2) + '01')

        df['creatDate_processed'] = pd.to_datetime(df['date_str'], format='%Y%m%d', errors='coerce')
        df['days_since_create'] = (df['creatDate_processed'] - base_date).dt.days

        # 处理异常日期
        days_median = df['days_since_create'].median()
        if pd.isna(days_median):
                days_median = 0
        df['days_since_create'] = df['days_since_create'].fillna(days_median)

        # 创建上线新鲜度特征（天数越少越新鲜）
        df['create_freshness'] = 1 / (df['days_since_create'].abs() + 1)

        print(f"上线时间特征处理完成，天数范围: {df['days_since_create'].min()} - {df['days_since_create'].max()}")


    # 11. 处理报价类型（offerType）- 重要特征！
    # 提供(0)通常比请求(1)价格更高
    if 'offerType' in df.columns:
        df['offerType'] = pd.to_numeric(df['offerType'], errors='coerce')
        offer_mode = df['offerType'].mode()
        if len(offer_mode) > 0:
            df['offerType'] = df['offerType'].fillna(offer_mode[0])
        else:
            df['offerType'] = df['offerType'].fillna(0)
        print(f"报价类型分布: {df['offerType'].value_counts().to_dict()}")

    # 12. 创建时间相关的交互特征
    if 'reg_year' in df.columns and 'create_year' in df.columns:
        # 注册到上线的年份差（车辆在市场上的流通时间）
        df['reg_to_create_years'] = df['create_year'] - df['reg_year']
        df['reg_to_create_years'] = df['reg_to_create_years'].clip(0, 30)  # 限制在合理范围

    # 13. 创建更多业务相关的特征
    # 品牌-车型组合特征
    if 'brand' in df.columns and 'model' in df.columns:
        df['brand_model'] = df['brand'].astype(str) + '_' + df['model'].astype(str)
        le_brand_model = LabelEncoder()
        df['brand_model'] = le_brand_model.fit_transform(df['brand_model'])

    # 功率密度特征（功率/车龄+1）
    df['power_age_ratio'] = df['power'] / (df['car_age'] + 1)

    # 地区-销售方特征
    if 'regionCode' in df.columns and 'seller' in df.columns:
        df['region_seller'] = df['regionCode'].astype(str) + '_' + df['seller'].astype(str)
        le_region_seller = LabelEncoder()
        df['region_seller'] = le_region_seller.fit_transform(df['region_seller'])

    # 报价类型与车龄的交互特征（不同报价类型对不同车龄的影响不同）
    if 'offerType' in df.columns:
        df['offer_age_interaction'] = df['offerType'] * df['car_age']

    # 里程与功率的交互特征
    df['km_power_ratio'] = df['kilometer'] / (df['power'] + 1)

    # 14. 只移除真正无用的列
    drop_cols = ['SaleID', 'name', 'regDate', 'creatDate', 'creatDate_processed', 'date_str']
    # 只移除存在的列
    drop_cols = [col for col in drop_cols if col in df.columns]
    df = df.drop(columns=drop_cols)

    # 15. 分离特征和目标变量
    if 'price' in df.columns:
        X = df.drop(columns=['price'])
        y = df['price']
        print(f"训练数据 - 特征数量: {X.shape[1]}, 样本数量: {X.shape[0]}")
    else:
        # 测试集没有price列
        X = df
        y = None
        print(f"测试数据 - 特征数量: {X.shape[1]}, 样本数量: {X.shape[0]}")

    print("最终特征列:", X.columns.tolist())
    return X, y


def train_model(X, y):
    """Train and evaluate the model"""

    # 数据划分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    print(f"训练集形状: {X_train.shape}")
    print(f"验证集形状: {X_test.shape}")

    # 初始化并训练模型
    # 根据MAE评价标准，使用RandomForest是合适的选择
    model = RandomForestRegressor(
        n_estimators=300,  # 增加树的数量
        max_depth=20,  # 适当增加深度
        min_samples_split=10,  # 防止过拟合
        min_samples_leaf=5,  # 防止过拟合
        max_features='sqrt',  # 特征子集大小
        random_state=42,
        n_jobs=-1
    )

    print("开始训练模型...")
    model.fit(X_train, y_train)
    print("模型训练完成!")

    # 模型评估
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"\n模型评估结果:")
    print(f"MAE (Mean Absolute Error): {mae:.2f}")

    # 计算其他评估指标
    mse = np.mean((y_test - y_pred) ** 2)
    rmse = np.sqrt(mse)
    print(f"RMSE (Root Mean Square Error): {rmse:.2f}")

    # 特征重要性分析
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 15 重要特征:")
    print(feature_importance.head(15).to_string(index=False))

    return model


def generate_submission(model, test_file, output_file):
    """Generate submission file in required format"""
    try:
        test_df = pd.read_csv(test_file, sep=r'\s+')
        print(f"测试数据加载成功，形状: {test_df.shape}")

        # 保存SaleID
        sale_ids = test_df['SaleID'].copy()

        # 应用相同的预处理
        X_test, _ = preprocess_data(test_df)

        # 预测
        predictions = model.predict(X_test)
        print(f"预测完成，预测结果数量: {len(predictions)}")
        print(f"预测价格范围: {predictions.min():.2f} - {predictions.max():.2f}")

        # 创建文件，格式按照题目要求
        submission = pd.DataFrame({
            'SaleID': sale_ids,
            'price': predictions
        })

        # 确保SaleID为整数格式
        submission['SaleID'] = submission['SaleID'].astype(int)
        submission['price'] = submission['price'].round(2)

        submission.to_csv(output_file, index=False)
        print(f"\n文件已保存为 {output_file}")


    except Exception as e:
        print(f"生成文件失败: {e}")


def main():
    print("二手车价格预测启动")
    print("=" * 50)

    # 加载训练数据
    train_file = 'used_car_train_20200313.csv'
    df = load_data(train_file)

    # 数据预处理
    print("\n开始数据预处理...")
    X, y = preprocess_data(df)

    print(f"\n数据统计信息:")
    print(f"目标变量price统计:")
    print(y.describe())

    # 训练模型
    print("\n开始模型训练...")
    model = train_model(X, y)
    print("\n模型训练完成!")

    # 生成测试结果
    test_file = 'used_car_testA_20200313.csv'

    print(f"\n开始生成文件...")
    generate_submission(model, test_file, 'Result.csv')
    print("\n项目执行完成！")


if __name__ == "__main__":
    main()