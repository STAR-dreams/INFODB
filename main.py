from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import os
import sqlite3
import json
import logging
from src.graph import graph_bp
from src.db_index import db_index_bp
from src.db_view import db_view_bp

info_explain = """
               用户使用说明
============================================
程序运行显示“ * Running on '______' ”
复制所给的网址，在浏览器中打开
初次进入网页需要注册账号，注册完成后进行登录
    用户名请不要使用“admin”和“user”
--------------------------------------------
平台主要功能：
    1. 数据统计分析
    2. 情报数据查看，搜索
    3. 数据库的增删改查操作
    (只有管理员具有对数据库操作的权限)
    4. 地图编辑功能，航路选择查看
        > 在左侧选择特定名称的航路单独显示
        > 图层编辑功能推荐使用“卫星图”地图
        > 进入“地图编辑”界面
        > 打开左侧浅灰色侧边栏可进行操作
        > 点击点坐标，航段，航路可以查看对应详情
--------------------------------------------
普通用户与管理员用户功能上存在差异
============================================

*** 重要提示：电脑防火墙可能阻止程序部分功能
注：此程序无恶意脚本，放心使用，如果出现此情况，
    点击同意后退出程序再次进入即可恢复其功能
    
"""
print(info_explain)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 注册蓝图
app.register_blueprint(graph_bp)
app.register_blueprint(db_index_bp)
app.register_blueprint(db_view_bp)

# 配置数据库路径
import sys
# 获取程序运行目录（exe文件所在目录）
if hasattr(sys, '_MEIPASS'):
    # 打包后的环境 - 使用PyInstaller的临时目录
    # 先尝试从MEIPASS目录获取数据库文件
    MEIPASS_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    
    # 检查MEIPASS中的db目录是否存在
    if os.path.exists(os.path.join(MEIPASS_DIR, 'db')):
        # 使用MEIPASS中的数据库文件作为源文件
        SRC_USER_DB = os.path.join(MEIPASS_DIR, 'db', 'user.sqlite')
        SRC_INFO_DB = os.path.join(MEIPASS_DIR, 'db', 'info.sqlite')
        
        # 目标数据库文件位置（exe文件所在目录）
        USER_DB_PATH = os.path.join(BASE_DIR, 'db', 'user.sqlite')
        INFO_DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        # 确保目标db目录存在
        os.makedirs(os.path.join(BASE_DIR, 'db'), exist_ok=True)
        
        # 如果目标数据库文件不存在，从MEIPASS复制
        import shutil
        if not os.path.exists(USER_DB_PATH):
            shutil.copy2(SRC_USER_DB, USER_DB_PATH)
        if not os.path.exists(INFO_DB_PATH):
            shutil.copy2(SRC_INFO_DB, INFO_DB_PATH)
    else:
        # 如果MEIPASS中没有db目录，使用exe所在目录
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
        USER_DB_PATH = os.path.join(BASE_DIR, 'db', 'user.sqlite')
        INFO_DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        os.makedirs(os.path.join(BASE_DIR, 'db'), exist_ok=True)
else:
    # 开发环境
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    USER_DB_PATH = os.path.join(BASE_DIR, 'db', 'user.sqlite')
    INFO_DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
    os.makedirs(os.path.join(BASE_DIR, 'db'), exist_ok=True)

# 初始化用户数据库
def init_user_db():
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 检查是否存在管理员用户
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    admin = cursor.fetchone()
    if not admin:
        # 创建默认管理员用户
        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                      ('admin', 'admin123', True))
    
    conn.commit()
    conn.close()

# 获取用户
def get_user(username):
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

# 获取用户通过ID
def get_user_by_id(user_id):
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# 添加用户
def add_new_user(username, password, is_admin=False):
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                      (username, password, is_admin))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# 更新用户
def update_user(user_id, username, password=None, is_admin=None):
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    try:
        if password:
            cursor.execute('UPDATE users SET username = ?, password = ?, is_admin = ? WHERE id = ?', 
                          (username, password, is_admin, user_id))
        else:
            cursor.execute('UPDATE users SET username = ?, is_admin = ? WHERE id = ?', 
                          (username, is_admin, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# 删除用户
def delete_user(user_id):
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

# 获取所有用户
def get_all_users():
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# 执行原生SQL查询
def execute_query(query, params=(), db_path=INFO_DB_PATH):
    # 确保数据库文件所在目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 尝试以可写模式打开数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

# 记录变更日志
def record_change_log(username, action, table_name, record_id, before_value, after_value, description):
    query = """
    INSERT INTO ChangeLog (UserID, Action, TableName, RecordID, BeforeValue, AfterValue, Description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query, (username, action, table_name, record_id, before_value, after_value, description))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"记录变更日志失败: {str(e)}")
        return False

# 获取表结构
def get_table_structure(table_name):
    query = "PRAGMA table_info({})".format(table_name)
    results = execute_query(query)
    columns = []
    for row in results:
        columns.append({
            'name': row['name'],
            'type': row['type'],
            'notnull': row['notnull'],
            'dflt_value': row['dflt_value'],
            'pk': row['pk']
        })
    return columns

# 获取表数据
def get_table_data(table_name, page=1, per_page=10, search_term=None):
    offset = (page - 1) * per_page
    
    if search_term:
        # 构建搜索条件
        columns = get_table_structure(table_name)
        search_conditions = []
        for column in columns:
            if column['type'] in ['TEXT', 'VARCHAR']:
                search_conditions.append(f"{column['name']} LIKE ?")
        
        if search_conditions:
            search_sql = " OR ".join(search_conditions)
            query = f"SELECT * FROM {table_name} WHERE {search_sql} LIMIT ? OFFSET ?"
            params = tuple(['%' + search_term + '%'] * len(search_conditions) + [per_page, offset])
            total_query = f"SELECT COUNT(*) FROM {table_name} WHERE {search_sql}"
            total_params = tuple(['%' + search_term + '%'] * len(search_conditions))
        else:
            # 如果没有文本列，直接查询
            query = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
            params = (per_page, offset)
            total_query = f"SELECT COUNT(*) FROM {table_name}"
            total_params = ()
    else:
        query = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
        params = (per_page, offset)
        total_query = f"SELECT COUNT(*) FROM {table_name}"
        total_params = ()
    
    results = execute_query(query, params)
    total = execute_query(total_query, total_params)[0][0]
    
    # 转换为字典列表
    data = []
    for row in results:
        row_dict = {}
        for key in row.keys():
            row_dict[key] = row[key]
        
        # 添加 id 属性，使用表的主键值
        # 处理不同表的主键名称
        primary_key_mapping = {
            'RouteSegment': 'SegmentID',
            'WaypointType': 'TypeID',
            'WaypointTypeMapping': 'MappingID',
            'ChangeLog': 'LogID',
            'RouteSegmentMapping': 'MappingID',
            'NavaidInfo': 'NavaidID'
        }
        
        primary_key = primary_key_mapping.get(table_name, f"{table_name}ID")
        
        if primary_key in row_dict:
            row_dict['id'] = row_dict[primary_key]
        
        data.append(row_dict)
    
    return {
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }

# 登录检查装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 路由定义
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = get_user(username)
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误！', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('两次输入的密码不一致！', 'danger')
            return render_template('register.html')
        
        existing_user = get_user(username)
        if existing_user:
            flash('用户名已存在！', 'danger')
            return render_template('register.html')
        
        success = add_new_user(username, password)
        if success:
            flash('注册成功，请登录！', 'success')
            return redirect(url_for('login'))
        else:
            flash('注册失败，请重试！', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('已退出登录！', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # 获取各表数据统计
    waypoint_count = execute_query("SELECT COUNT(*) FROM Waypoint")[0][0]
    route_count = execute_query("SELECT COUNT(*) FROM Route")[0][0]
    navaid_count = execute_query("SELECT COUNT(*) FROM NavaidInfo")[0][0]
    log_count = execute_query("SELECT COUNT(*) FROM ChangeLog")[0][0]
    segment_count = execute_query("SELECT COUNT(*) FROM RouteSegment")[0][0]
    waypoint_type_count = execute_query("SELECT COUNT(*) FROM WaypointType")[0][0]
    
    # 获取航路点类型分布
    waypoint_type_results = execute_query("""
        SELECT wt.TypeName, COUNT(wtm.WaypointID) as count
        FROM WaypointType wt
        LEFT JOIN WaypointTypeMapping wtm ON wt.TypeID = wtm.TypeID
        GROUP BY wt.TypeName
        ORDER BY count DESC
    """)
    waypoint_types = []
    waypoint_type_counts = []
    for row in waypoint_type_results:
        waypoint_types.append(row['TypeName'])
        waypoint_type_counts.append(row['count'])
    
    # 获取航线类型分布
    route_type_results = execute_query("""
        SELECT RouteType, COUNT(*) as count
        FROM Route
        GROUP BY RouteType
        ORDER BY count DESC
    """)
    route_type_data = []
    for row in route_type_results:
        route_type_data.append({'value': row['count'], 'name': row['RouteType']})
    
    # 获取最近的变更日志
    recent_logs = execute_query("""
        SELECT * FROM ChangeLog
        ORDER BY ActionTime DESC
        LIMIT 10
    """)
    
    # 计算航线总长
    total_distance_result = execute_query("""
        SELECT SUM(DistanceKM) as total
        FROM RouteSegment
    """)
    total_distance = total_distance_result[0]['total'] or 0
    
    return render_template('dashboard.html',
                           waypoint_count=waypoint_count,
                           route_count=route_count,
                           navaid_count=navaid_count,
                           log_count=log_count,
                           segment_count=segment_count,
                           waypoint_type_count=waypoint_type_count,
                           waypoint_types=waypoint_types,
                           waypoint_type_counts=waypoint_type_counts,
                           route_type_data=route_type_data,
                           recent_logs=recent_logs,
                           total_distance=total_distance,
                           sqlite_version=sqlite3.version,
                           now=datetime.now())

@app.route('/data/view/<string:table>')
@login_required
def data_view(table):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    keyword = request.args.get('keyword', '')
    sort_by = request.args.get('sort_by', '')
    sort_order = request.args.get('sort_order', 'asc')
    
    # 检查表是否存在
    tables = [
        'Waypoint', 'WaypointType', 'WaypointTypeMapping',
        'NavaidInfo', 'RouteSegment', 'Route',
        'RouteSegmentMapping', 'ChangeLog'
    ]
    
    if table not in tables:
        flash('无效的表名！', 'danger')
        return redirect(url_for('dashboard'))
    
    # 获取表数据
    result = get_table_data(table, page, per_page, keyword)
    records = result['data']
    total = result['total']
    total_pages = result['total_pages']
    
    # 获取表结构
    columns = get_table_structure(table)
    
    # 构建分页对象
    pagination = {
        'current_page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'start': (page - 1) * per_page,
        'end': min(page * per_page, total)
    }
    
    # 构建表描述
    table_descriptions = {
        'Waypoint': '航路点表',
        'WaypointType': '航路点类型表',
        'WaypointTypeMapping': '航路点类型联系表',
        'NavaidInfo': '导航台专属属性表',
        'RouteSegment': '航段表',
        'Route': '航线表',
        'RouteSegmentMapping': '航段-航线关系表',
        'ChangeLog': '数据变更日志表'
    }
    table_description = table_descriptions.get(table, table)
    
    # 构建过滤器
    filters = []
    filter_values = {}
    
    # 构建列信息
    table_columns = []
    for col in columns:
        table_columns.append({
            'name': col['name'],
            'label': col['name'],
            'type': col['type'],
            'sortable': True
        })
    
    return render_template('data_view.html', 
                          table_name=table,
                          records=records,
                          columns=table_columns,
                          pagination=pagination,
                          table_description=table_description,
                          filters=filters,
                          filter_values=filter_values,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          keyword=keyword)

@app.route('/data/manage/<string:table>/<string:action>', methods=['GET', 'POST'])
@login_required
def data_manage(table, action):
    if not session.get('is_admin'):
        flash('只有管理员可以执行此操作！', 'danger')
        return redirect(url_for('data_view', table=table))
    
    if action == 'add':
        if request.method == 'POST':
            # 处理添加数据
            columns = get_table_structure(table)
            column_names = [col['name'] for col in columns if not col['pk']]
            
            placeholders = ','.join(['?' for _ in column_names])
            cols = ','.join(column_names)
            
            values = []
            for col in column_names:
                value = request.form.get(col)
                values.append(value)
            
            # 获取说明
            description = request.form.get('description', '')
            
            query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            try:
                conn = sqlite3.connect(INFO_DB_PATH)
                cursor = conn.cursor()
                cursor.execute(query, values)
                # 获取插入的记录ID
                record_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                # 记录变更日志
                after_value = {}
                for i, col in enumerate(column_names):
                    after_value[col] = values[i]
                record_change_log(
                    session['username'],
                    '添加',
                    table,
                    record_id,
                    '{}',
                    json.dumps(after_value),
                    description
                )
                
                # 返回重定向响应
                flash('数据添加成功！', 'success')
                return redirect(url_for('data_view', table=table))
            except sqlite3.IntegrityError as e:
                conn.close()
                if 'UNIQUE constraint failed' in str(e):
                    flash('数据添加失败：记录已存在，请使用不同的值', 'danger')
                else:
                    flash(f'数据库操作失败：{str(e)}', 'danger')
                return redirect(url_for('data_manage', table=table, action=action))
            except sqlite3.OperationalError as e:
                flash(f'数据库操作失败：{str(e)}', 'danger')
                return redirect(url_for('data_manage', table=table, action=action))
        
        columns = get_table_structure(table)
        # 构建字段信息
        fields = []
        print(f"获取到的表结构: {columns}")
        for col in columns:
            if not col['pk']:
                # 类型映射
                field_type = col['type']
                if 'datetime' in field_type.lower() or 'timestamp' in field_type.lower():
                    field_type = 'datetime'
                elif 'date' in field_type.lower():
                    field_type = 'date'
                elif 'int' in field_type.lower():
                    field_type = 'integer'
                elif 'float' in field_type.lower() or 'decimal' in field_type.lower():
                    field_type = 'float'
                elif 'bool' in field_type.lower():
                    field_type = 'boolean'
                else:
                    field_type = 'string'
                
                fields.append({
                    'name': col['name'],
                    'label': col['name'],
                    'type': field_type,
                    'required': col['notnull'],
                    'disabled': False,
                    'help_text': '',
                    'placeholder': f'请输入{col["name"]}',
                    'maxlength': 255
                })
        print(f"构建的字段信息: {fields}")
        
        return render_template('data_manage.html', 
                              table_name=table,
                              action=action,
                              fields=fields,
                              record={},
                              table_description=table)
    
    elif action == 'edit':
        record_id = request.args.get('id')
        if not record_id:
            flash('缺少记录ID！', 'danger')
            return redirect(url_for('data_view', table=table))
        
        # 处理不同表的主键名称
        primary_key_mapping = {
            'RouteSegment': 'SegmentID',
            'WaypointType': 'TypeID',
            'WaypointTypeMapping': 'MappingID',
            'ChangeLog': 'LogID',
            'RouteSegmentMapping': 'MappingID',
            'NavaidInfo': 'NavaidID'
        }
        
        primary_key = primary_key_mapping.get(table, f"{table}ID")
        
        # 获取记录数据
        query = f"SELECT * FROM {table} WHERE {primary_key} = ?"
        result = execute_query(query, (record_id,))
        if not result:
            flash('记录不存在！', 'danger')
            return redirect(url_for('data_view', table=table))
        
        record = result[0]
        
        if request.method == 'POST':
            # 处理更新数据
            columns = get_table_structure(table)
            updates = []
            values = []
            
            # 获取编辑前的值
            before_value = {}
            for col in columns:
                if not col['pk']:
                    before_value[col['name']] = record[col['name']]
            
            # 获取编辑后的值
            after_value = {}
            for col in columns:
                if not col['pk']:
                    updates.append(f"{col['name']} = ?")
                    value = request.form.get(col['name'])
                    values.append(value)
                    after_value[col['name']] = value
            
            # 获取说明
            description = request.form.get('description', '')
            
            values.append(record_id)
            update_str = ','.join(updates)
            
            # 处理不同表的主键名称
            primary_key_mapping = {
            'RouteSegment': 'SegmentID',
            'WaypointType': 'TypeID',
            'WaypointTypeMapping': 'MappingID',
            'ChangeLog': 'LogID',
            'RouteSegmentMapping': 'MappingID',
            'NavaidInfo': 'NavaidID'
        }
            
            primary_key = primary_key_mapping.get(table, f"{table}ID")
            
            query = f"UPDATE {table} SET {update_str} WHERE {primary_key} = ?"
            try:
                conn = sqlite3.connect(INFO_DB_PATH)
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                conn.close()
                
                # 记录变更日志
                record_change_log(
                    session['username'],
                    '修改',
                    table,
                    record_id,
                    json.dumps(before_value),
                    json.dumps(after_value),
                    description
                )
                
                # 使用 flash 消息和重定向代替 JSON 响应
                flash('数据更新成功！', 'success')
                return redirect(url_for('data_view', table=table))
            except sqlite3.IntegrityError as e:
                conn.close()
                if 'UNIQUE constraint failed' in str(e):
                    # 使用 flash 消息和重定向代替 JSON 响应
                    flash('数据更新失败：记录已存在，请使用不同的值', 'danger')
                    return redirect(url_for('data_manage', table=table, action=action, id=record_id))
                else:
                    # 使用 flash 消息和重定向代替 JSON 响应
                    flash(f'数据库操作失败：{str(e)}', 'danger')
                    return redirect(url_for('data_manage', table=table, action=action, id=record_id))
            except sqlite3.OperationalError as e:
                # 使用 flash 消息和重定向代替 JSON 响应
                flash(f'数据库操作失败：{str(e)}', 'danger')
                return redirect(url_for('data_manage', table=table, action=action, id=record_id))
    
        columns = get_table_structure(table)
        # 构建字段信息
        fields = []
        for col in columns:
            if not col['pk']:
                # 类型映射
                field_type = col['type']
                if 'datetime' in field_type.lower() or 'timestamp' in field_type.lower():
                    field_type = 'datetime'
                elif 'date' in field_type.lower():
                    field_type = 'date'
                elif 'int' in field_type.lower():
                    field_type = 'integer'
                elif 'float' in field_type.lower() or 'decimal' in field_type.lower():
                    field_type = 'float'
                elif 'bool' in field_type.lower():
                    field_type = 'boolean'
                else:
                    field_type = 'string'
                
                fields.append({
                    'name': col['name'],
                    'label': col['name'],
                    'type': field_type,
                    'required': col['notnull'],
                    'disabled': False,
                    'help_text': '',
                    'placeholder': f'请输入{col["name"]}',
                    'maxlength': 255
                })
        
        return render_template('data_manage.html', 
                              table_name=table,
                              action=action,
                              fields=fields,
                              record=record,
                              table_description=table,
                              id=record_id)
    
    elif action == 'delete':
        record_id = request.form.get('id') or request.args.get('id')
        if not record_id:
            flash('缺少记录ID！', 'danger')
            return redirect(url_for('data_view', table=table))
        
        # 处理不同表的主键名称
        primary_key_mapping = {
                'RouteSegment': 'SegmentID',
                'WaypointType': 'TypeID',
                'WaypointTypeMapping': 'MappingID',
                'ChangeLog': 'LogID',
                'RouteSegmentMapping': 'MappingID',
                'NavaidInfo': 'NavaidID'
            }
        
        primary_key = primary_key_mapping.get(table, f"{table}ID")
        
        # 获取删除前的记录值
        query_get = f"SELECT * FROM {table} WHERE {primary_key} = ?"
        result = execute_query(query_get, (record_id,))
        before_value = {}
        if result:
            record = result[0]
            columns = get_table_structure(table)
            for col in columns:
                if not col['pk']:
                    before_value[col['name']] = record[col['name']]
        
        # 获取说明
        description = request.form.get('description', '')
        
        # 删除记录
        query = f"DELETE FROM {table} WHERE {primary_key} = ?"
        try:
            conn = sqlite3.connect(INFO_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(query, (record_id,))
            conn.commit()
            conn.close()
            
            # 记录变更日志
            record_change_log(
                session['username'],
                '删除',
                table,
                record_id,
                json.dumps(before_value),
                '{}',
                description
            )
            
            # 使用 flash 消息和重定向代替 JSON 响应
            flash('数据删除成功！', 'success')
            return redirect(url_for('data_view', table=table))
        except sqlite3.OperationalError as e:
            # 使用 flash 消息和重定向代替 JSON 响应
            flash(f'数据库操作失败：{str(e)}', 'danger')
            return redirect(url_for('data_view', table=table))
    
    return redirect(url_for('data_view', table=table))

@app.route('/map')
@login_required
def map_page():
    # 获取航路点数据
    waypoints = execute_query("""
        SELECT w.*, wt.TypeName as type_name
        FROM Waypoint w
        LEFT JOIN WaypointTypeMapping wtm ON w.WaypointID = wtm.WaypointID
        LEFT JOIN WaypointType wt ON wtm.TypeID = wt.TypeID
        WHERE w.IsActive = 1
    """)
    
    # 获取导航台数据
    navaids = execute_query("""
        SELECT * FROM NavaidInfo
    """)
    
    # 获取航线数据
    routes = execute_query("""
        SELECT * FROM Route
    """)
    
    # 获取航段数据
    segments = execute_query("""
        SELECT * FROM RouteSegment
    """)
    
    # 获取航段-航线映射
    route_segment_mappings = execute_query("""
        SELECT * FROM RouteSegmentMapping
    """)
    
    # 构建航路点字典，方便后续查找
    waypoint_dict = {}
    for wp in waypoints:
        waypoint_dict[wp['WaypointID']] = {
            'id': wp['WaypointID'],
            'name': wp['Name'],
            'latitude': wp['Latitude'],
            'longitude': wp['Longitude'],
            'type_name': wp['type_name'] or '未知'
        }
    
    # 构建航段字典
    segment_dict = {}
    for seg in segments:
        segment_dict[seg['SegmentID']] = {
            'id': seg['SegmentID'],
            'start_id': seg['StartWaypointID'],
            'end_id': seg['EndWaypointID'],
            'distance': seg['DistanceKM']
        }
    
    # 构建航线数据，包含路径点
    route_data = []
    for route in routes:
        # 查找该航线的所有航段
        route_segments = []
        for mapping in route_segment_mappings:
            if mapping['RouteID'] == route['RouteID']:
                route_segments.append(mapping['SegmentID'])
        
        # 构建航线路径
        path = []
        for seg_id in route_segments:
            seg = segment_dict.get(seg_id)
            if seg:
                start_wp = waypoint_dict.get(seg['start_id'])
                end_wp = waypoint_dict.get(seg['end_id'])
                if start_wp:
                    path.append([start_wp['latitude'], start_wp['longitude']])
                if end_wp:
                    path.append([end_wp['latitude'], end_wp['longitude']])
        
        route_data.append({
            'id': route['RouteID'],
            'name': route['RouteName'],
            'type_name': route['RouteType'],
            'path': path
        })
    
    # 构建导航台数据
    navaid_data = []
    for navaid in navaids:
        # 查找对应的航路点
        wp = execute_query("""
            SELECT * FROM Waypoint
            WHERE WaypointID = ?
        """, (navaid['WaypointID'],))
        
        if wp:
            navaid_data.append({
                'id': navaid['NavaidID'],
                'name': wp[0]['Name'],
                'latitude': wp[0]['Latitude'],
                'longitude': wp[0]['Longitude'],
                'type_name': '未知',
                'frequency': navaid['Frequency']
            })
    
    # 构建最终的航路点数据
    final_waypoint_data = []
    for wp_id, wp in waypoint_dict.items():
        final_waypoint_data.append(wp)
    
    # 统计数据
    waypoint_count = len(final_waypoint_data)
    route_count = len(route_data)
    navaid_count = len(navaid_data)
    route_type_count = len(set(r['type_name'] for r in route_data))
    
    return render_template('map.html', 
                          waypoints=final_waypoint_data,
                          routes=route_data,
                          navaids=navaid_data,
                          waypoint_count=waypoint_count,
                          route_count=route_count,
                          navaid_count=navaid_count,
                          route_type_count=route_type_count,
                          airport_count=0,
                          airspace_count=0)

@app.route('/users')
@login_required
def users():
    if not session.get('is_admin'):
        flash('只有管理员可以访问此页面！', 'danger')
        return redirect(url_for('dashboard'))
    
    all_users = get_all_users()
    return render_template('user_manage.html', users=all_users)

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if not session.get('is_admin'):
        flash('只有管理员可以执行此操作！', 'danger')
        return redirect(url_for('users'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if password != confirm_password:
        flash('两次输入的密码不一致！', 'danger')
        return redirect(url_for('users'))
    
    success = add_new_user(username, password, is_admin)
    if success:
        flash('用户添加成功！', 'success')
    else:
        flash('用户添加失败，用户名可能已存在！', 'danger')
    
    return redirect(url_for('users'))

@app.route('/user/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 检查用户名是否已存在
        existing_user = get_user(username)
        if existing_user and existing_user['id'] != session['user_id']:
            flash('用户名已存在！', 'danger')
            return redirect(url_for('user_settings'))
        
        # 更新用户信息
        user = get_user_by_id(session['user_id'])
        if password:
            if password != confirm_password:
                flash('两次输入的密码不一致！', 'danger')
                return redirect(url_for('user_settings'))
            update_user(session['user_id'], username, password, user['is_admin'])
        else:
            update_user(session['user_id'], username, None, user['is_admin'])
        
        session['username'] = username
        flash('个人设置更新成功！', 'success')
        return redirect(url_for('dashboard'))
    
    user = get_user_by_id(session['user_id'])
    return render_template('user_manage.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user_route(user_id):
    if not session.get('is_admin'):
        flash('只有管理员可以执行此操作！', 'danger')
        return redirect(url_for('users'))
    
    # 防止删除管理员用户
    if user_id == 1:
        flash('不能删除管理员用户！', 'danger')
        return redirect(url_for('users'))
    
    delete_user(user_id)
    flash('用户删除成功！', 'success')
    return redirect(url_for('users'))

@app.route('/api/waypoints')
@login_required
def get_waypoints_api():
    # 获取航路点数据
    waypoints = execute_query("""
        SELECT * FROM Waypoint
    """)
    
    # 转换为字典列表
    waypoint_list = []
    for waypoint in waypoints:
        waypoint_list.append({
            'WaypointID': waypoint['WaypointID'],
            'Name': waypoint['Name'],
            'Latitude': waypoint['Latitude'],
            'Longitude': waypoint['Longitude'],
            'IsActive': waypoint['IsActive']
        })
    
    return jsonify({
        'success': True,
        'waypoints': waypoint_list
    })

@app.route('/api/navaids')
@login_required
def get_navaids_api():
    # 获取导航台数据，关联Waypoint表获取坐标
    navaids = execute_query("""
        SELECT n.*, w.Latitude, w.Longitude, w.Name as WaypointName
        FROM NavaidInfo n
        LEFT JOIN Waypoint w ON n.WaypointID = w.WaypointID
    """)
    
    # 转换为字典列表
    navaid_list = []
    for navaid in navaids:
        navaid_list.append({
            'NavaidID': navaid['NavaidID'],
            'WaypointID': navaid['WaypointID'],
            'WaypointName': navaid['WaypointName'],
            'Latitude': navaid['Latitude'],
            'Longitude': navaid['Longitude'],
            'Frequency': navaid['Frequency']
        })
    
    return jsonify({
        'success': True,
        'navaids': navaid_list
    })

@app.route('/api/segments')
@login_required
def get_segments_api():
    # 获取航段数据，关联Waypoint表获取起点和终点坐标
    segments = execute_query("""
        SELECT rs.*, 
               ws.Latitude as StartLatitude, ws.Longitude as StartLongitude, ws.Name as StartName,
               we.Latitude as EndLatitude, we.Longitude as EndLongitude, we.Name as EndName
        FROM RouteSegment rs
        LEFT JOIN Waypoint ws ON rs.StartWaypointID = ws.WaypointID
        LEFT JOIN Waypoint we ON rs.EndWaypointID = we.WaypointID
    """)
    
    # 转换为字典列表
    segment_list = []
    for segment in segments:
        segment_list.append({
            'SegmentID': segment['SegmentID'],
            'StartWaypointID': segment['StartWaypointID'],
            'EndWaypointID': segment['EndWaypointID'],
            'StartName': segment['StartName'],
            'EndName': segment['EndName'],
            'StartLatitude': segment['StartLatitude'],
            'StartLongitude': segment['StartLongitude'],
            'EndLatitude': segment['EndLatitude'],
            'EndLongitude': segment['EndLongitude'],
            'DistanceKM': segment['DistanceKM'],
            'Direction': segment['Direction'],
            'MinAltitude': segment['MinAltitude']
        })
    
    return jsonify({
        'success': True,
        'segments': segment_list
    })

@app.route('/api/routes')
@login_required
def get_routes_api():
    # 获取所有航路及其关联的航段
    routes = execute_query("""
        SELECT r.*, 
               ws.Name as StartWaypointName, 
               we.Name as EndWaypointName
        FROM Route r
        LEFT JOIN Waypoint ws ON r.StartWaypointID = ws.WaypointID
        LEFT JOIN Waypoint we ON r.EndWaypointID = we.WaypointID
    """)
    
    route_list = []
    for route in routes:
        # 获取该航路的所有航段映射
        mappings = execute_query("""
            SELECT rsm.*, 
                   rs.StartWaypointID, rs.EndWaypointID,
                   ws.Latitude as StartLatitude, ws.Longitude as StartLongitude, ws.Name as StartName,
                   we.Latitude as EndLatitude, we.Longitude as EndLongitude, we.Name as EndName
            FROM RouteSegmentMapping rsm
            LEFT JOIN RouteSegment rs ON rsm.SegmentID = rs.SegmentID
            LEFT JOIN Waypoint ws ON rs.StartWaypointID = ws.WaypointID
            LEFT JOIN Waypoint we ON rs.EndWaypointID = we.WaypointID
            WHERE rsm.RouteID = ?
            ORDER BY rsm.SequenceNumber
        """, (route['RouteID'],))
        
        # 构建航段列表
        segments = []
        for mapping in mappings:
            segments.append({
                'MappingID': mapping['MappingID'],
                'SegmentID': mapping['SegmentID'],
                'SequenceNumber': mapping['SequenceNumber'],
                'IsReversed': mapping['IsReversed'],
                'StartWaypointID': mapping['StartWaypointID'],
                'EndWaypointID': mapping['EndWaypointID'],
                'StartName': mapping['StartName'],
                'EndName': mapping['EndName'],
                'StartLatitude': mapping['StartLatitude'],
                'StartLongitude': mapping['StartLongitude'],
                'EndLatitude': mapping['EndLatitude'],
                'EndLongitude': mapping['EndLongitude']
            })
        
        route_list.append({
            'RouteID': route['RouteID'],
            'RouteName': route['RouteName'],
            'RouteType': route['RouteType'],
            'StartWaypointID': route['StartWaypointID'],
            'EndWaypointID': route['EndWaypointID'],
            'StartWaypointName': route['StartWaypointName'],
            'EndWaypointName': route['EndWaypointName'],
            'TotalDistanceKM': route['TotalDistanceKM'],
            'Segments': segments
        })
    
    return jsonify({
        'success': True,
        'routes': route_list
    })

@app.route('/draw')
@login_required
def draw_page():
    return render_template('draw.html')

@app.route('/graph_redact')
@login_required
def graph_redact_page():
    return render_template('graph_redact.html')

@app.route('/data/view/route_details')
@login_required
def route_details_view():
    # 使用db_view.py中的API获取航路数据
    import requests
    try:
        # 调用本地API获取航路数据
        response = requests.get('http://localhost:5000/api/routes/details')
        data = response.json()
        
        if data.get('success'):
            routes = data.get('routes', [])
            
            # 构建列信息
            columns = [
                {'name': '序号', 'label': '序号', 'type': 'integer', 'sortable': True},
                {'name': '航路名', 'label': '航路名', 'type': 'text', 'sortable': True},
                {'name': '起点', 'label': '起点', 'type': 'text', 'sortable': True},
                {'name': '终点', 'label': '终点', 'type': 'text', 'sortable': True},
                {'name': '航路类型', 'label': '航路类型', 'type': 'text', 'sortable': True},
                {'name': '总距离', 'label': '总距离', 'type': 'float', 'sortable': True},
                {'name': '最低飞行高（KM）', 'label': '最低飞行高（KM）', 'type': 'float', 'sortable': True},
                {'name': '航段数量', 'label': '航段数量', 'type': 'integer', 'sortable': True},
                {'name': '创建时间', 'label': '创建时间', 'type': 'date', 'sortable': True},
                {'name': '维护时间', 'label': '维护时间', 'type': 'date', 'sortable': True}
            ]
            
            # 构建分页对象
            pagination = {
                'current_page': 1,
                'per_page': len(routes),
                'total': len(routes),
                'total_pages': 1,
                'start': 0,
                'end': len(routes)
            }
            
            return render_template('data_view.html', 
                                  table_name='RouteDetails',
                                  records=routes,
                                  columns=columns,
                                  pagination=pagination,
                                  table_description='航路数据视图',
                                  filters=[],
                                  filter_values={},
                                  sort_by='',
                                  sort_order='asc',
                                  keyword='')
        else:
            flash('获取航路数据失败！', 'danger')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"获取航路数据失败: {e}")
        flash('获取航路数据失败！', 'danger')
        return redirect(url_for('dashboard'))

# 存储访问日志
access_logs = []

# 自定义日志处理器
class AccessLogHandler(logging.Handler):
    def emit(self, record):
        if hasattr(record, 'request'):
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method': getattr(record.request, 'method', ''),
                'path': getattr(record.request, 'path', ''),
                'status': getattr(record, 'status', 0),
                'remote_addr': getattr(record.request, 'remote_addr', ''),
                'user_agent': getattr(record.request, 'user_agent', ''),
                'message': record.getMessage()
            }
            access_logs.append(log_entry)
            # 限制日志数量，只保留最近100条
            if len(access_logs) > 100:
                access_logs.pop(0)

# 配置日志
def setup_logging():
    handler = AccessLogHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

# 获取访问日志API
@app.route('/api/access-logs')
@login_required
def get_access_logs():
    return jsonify({
        'success': True,
        'logs': access_logs
    })

# 请求日志中间件
@app.after_request
def log_request(response):
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'remote_addr': request.remote_addr,
        'user_agent': str(request.user_agent),
        'message': f'{request.method} {request.path} {response.status_code}'
    }
    access_logs.append(log_entry)
    # 限制日志数量，只保留最近100条
    if len(access_logs) > 100:
        access_logs.pop(0)
    return response

# 主函数
if __name__ == '__main__':

    # 初始化用户数据库
    init_user_db()
    
    # 配置日志
    setup_logging()
    
    # 运行应用
    app.run(debug=True, host='0.0.0.0', port=5000)
