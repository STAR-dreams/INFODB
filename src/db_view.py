import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
import sqlite3
import json

# 创建蓝图
db_view_bp = Blueprint('db_view', __name__)

# 配置数据库路径
import sys
# 获取程序运行目录（exe文件所在目录）
if hasattr(sys, '_MEIPASS'):
    # 打包后的环境
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 开发环境
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 确保db目录存在
os.makedirs(os.path.join(BASE_DIR, 'db'), exist_ok=True)

INFO_DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')

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

# 登录检查装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 数据查看页面
@db_view_bp.route('/database_view/<table>')
@db_view_bp.route('/database_view')
def database_view(table='Waypoint'):
    return render_template('database_view.html', table=table)

# 获取航路点数据API端点
@db_view_bp.route('/api/waypoints/details')
def get_waypoints_details():
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        
        # 尝试使用Waypoint表（单数形式）
        cursor.execute('''
            SELECT 
                w.WaypointID,
                w.Name,
                w.Latitude,
                w.Longitude,
                w.IsActive,
                wt.TypeCode,
                wt.TypeName,
                n.Frequency,
                w.CreatedAt,
                w.UpdatedAt
            FROM 
                Waypoint w
            LEFT JOIN 
                WaypointTypeMapping wtm ON w.WaypointID = wtm.WaypointID
            LEFT JOIN 
                WaypointType wt ON wtm.TypeID = wt.TypeID
            LEFT JOIN 
                NavaidInfo n ON w.WaypointID = n.WaypointID
            ORDER BY 
                w.WaypointID
        ''')
        
        waypoints = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        waypoint_list = []
        for i, wp in enumerate(waypoints, 1):
            # 处理可能的空值
            waypoint_data = {
                '序号': i,
                'WaypointID': wp[0],
                '点名称': wp[1] if wp[1] is not None else '',
                '纬度': wp[2] if wp[2] is not None else '',
                '经度': wp[3] if wp[3] is not None else '',
                '状态': '有效' if wp[4] == 1 else '停用',
                '点类型': wp[5] if wp[5] is not None else '',
                '类型名称': wp[6] if wp[6] is not None else '',
                '频率': wp[7] if wp[7] is not None else '',
                '创建时间': wp[8] if wp[8] is not None else '',
                '维护时间': wp[9] if wp[9] is not None else ''
            }
            waypoint_list.append(waypoint_data)
        
        return jsonify({
            'success': True,
            'waypoints': waypoint_list
        })
    except Exception as e:
        print(f"获取航路点数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取航路点数据失败: {str(e)}'
        })

# 数据管理页面
@db_view_bp.route('/data/manage/<table_name>/<action>', methods=['GET', 'POST'])
@login_required
def data_manage(table_name, action):
    try:
        # 检查是否为管理员
        if not session.get('is_admin'):
            return jsonify({
                'success': False,
                'message': '权限不足，只有管理员可以执行此操作'
            }), 403
        
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if action == 'add':
            if request.method == 'GET':
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                conn.close()
                
                # 构建字段信息
                fields = []
                for col in columns:
                    if col[5] != 1:  # 不是主键
                        field_type = col[2]
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
                            'name': col[1],
                            'label': col[1],
                            'type': field_type,
                            'required': col[3],
                            'disabled': False,
                            'help_text': '',
                            'placeholder': f'请输入{col[1]}',
                            'maxlength': 255
                        })
                
                # 显示添加表单
                return render_template('data_manage.html', 
                                      table_name=table_name, 
                                      action='add',
                                      fields=fields,
                                      record={},
                                      table_description=table_name)
            elif request.method == 'POST':
                # 处理添加数据
                data = request.form.to_dict()
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # 构建插入语句
                column_names = []
                values = []
                placeholders = []
                
                for col in columns:
                    if col[5] != 1:  # 不是主键
                        col_name = col[1]
                        if col_name in data:
                            column_names.append(col_name)
                            values.append(data.get(col_name))
                            placeholders.append('?')
                
                if column_names:
                    cols_str = ','.join(column_names)
                    placeholders_str = ','.join(placeholders)
                    
                    try:
                        cursor.execute(f'''
                            INSERT INTO {table_name} ({cols_str})
                            VALUES ({placeholders_str})
                        ''', values)
                        conn.commit()
                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': '数据添加成功'
                        })
                    except sqlite3.IntegrityError as e:
                        conn.close()
                        if 'UNIQUE constraint failed' in str(e):
                            return jsonify({
                                'success': False,
                                'message': '数据添加失败：记录已存在，请使用不同的值'
                            }), 400
                        else:
                            return jsonify({
                                'success': False,
                                'message': f'数据添加失败: {str(e)}'
                            }), 400
                else:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': '没有可插入的字段'
                    }), 400
        
        elif action == 'view':
            # 查看数据详情
            record_id = request.args.get('id')
            if not record_id:
                return jsonify({
                    'success': False,
                    'message': '缺少记录ID'
                }), 400
            
            if table_name == 'Waypoint':
                cursor.execute('SELECT * FROM Waypoint WHERE WaypointID = ?', (record_id,))
                record = cursor.fetchone()
                conn.close()
                if record:
                    return jsonify({
                        'success': True,
                        'record': record
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '记录不存在'
                    }), 404
        
        elif action == 'edit':
            if request.method == 'GET':
                # 查看数据详情
                record_id = request.args.get('id')
                if not record_id:
                    return jsonify({
                        'success': False,
                        'message': '缺少记录ID'
                    }), 400
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # 获取记录数据
                if table_name == 'Waypoint':
                    cursor.execute('SELECT * FROM Waypoint WHERE WaypointID = ?', (record_id,))
                    record = cursor.fetchone()
                elif table_name == 'Route':
                    cursor.execute('SELECT * FROM Route WHERE RouteID = ?', (record_id,))
                    record = cursor.fetchone()
                elif table_name == 'RouteSegment':
                    cursor.execute('SELECT * FROM RouteSegment WHERE SegmentID = ?', (record_id,))
                    record = cursor.fetchone()
                elif table_name == 'NavaidInfo':
                    cursor.execute('SELECT * FROM NavaidInfo WHERE NavaidID = ?', (record_id,))
                    record = cursor.fetchone()
                elif table_name == 'WaypointType':
                    cursor.execute('SELECT * FROM WaypointType WHERE TypeID = ?', (record_id,))
                    record = cursor.fetchone()
                else:
                    # 默认尝试使用通用ID字段
                    cursor.execute(f'SELECT * FROM {table_name} WHERE {table_name}ID = ?', (record_id,))
                    record = cursor.fetchone()
                
                conn.close()
                
                if not record:
                    return jsonify({
                        'success': False,
                        'message': '记录不存在'
                    }), 404
                
                # 构建字段信息
                fields = []
                for col in columns:
                    if col[5] != 1:  # 不是主键
                        field_type = col[2]
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
                            'name': col[1],
                            'label': col[1],
                            'type': field_type,
                            'required': col[3],
                            'disabled': False,
                            'help_text': '',
                            'placeholder': f'请输入{col[1]}',
                            'maxlength': 255
                        })
                
                # 构建记录字典
                record_dict = {}
                for i, col in enumerate(columns):
                    record_dict[col[1]] = record[i]
                
                # 显示编辑表单
                return render_template('data_manage.html', 
                                      table_name=table_name, 
                                      action='edit',
                                      fields=fields,
                                      record=record_dict,
                                      table_description=table_name,
                                      id=record_id)
            elif request.method == 'POST':
                # 处理编辑数据
                record_id = request.form.get('id')
                data = request.form.to_dict()
                if not record_id:
                    return jsonify({
                        'success': False,
                        'message': '缺少记录ID'
                    }), 400
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # 构建更新语句
                updates = []
                values = []
                
                primary_key = None
                for col in columns:
                    if col[5] == 1:  # 是主键
                        primary_key = col[1]
                    else:
                        col_name = col[1]
                        if col_name in data:
                            updates.append(f"{col_name} = ?")
                            values.append(data.get(col_name))
                
                if updates and primary_key:
                    values.append(record_id)
                    update_str = ','.join(updates)
                    
                    try:
                        cursor.execute(f'''
                            UPDATE {table_name} SET {update_str}
                            WHERE {primary_key} = ?
                        ''', values)
                        conn.commit()
                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': '数据更新成功'
                        })
                    except sqlite3.IntegrityError as e:
                        conn.close()
                        if 'UNIQUE constraint failed' in str(e):
                            return jsonify({
                                'success': False,
                                'message': '数据更新失败：记录已存在，请使用不同的值'
                            }), 400
                        else:
                            return jsonify({
                                'success': False,
                                'message': f'数据更新失败: {str(e)}'
                            }), 400
                else:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': '没有可更新的字段或缺少主键'
                    }), 400
        
        elif action == 'delete':
            # 处理删除数据
            record_id = request.form.get('id')
            if not record_id:
                return jsonify({
                    'success': False,
                    'message': '缺少记录ID'
                }), 400
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # 找到主键
            primary_key = None
            for col in columns:
                if col[5] == 1:  # 是主键
                    primary_key = col[1]
                    break
            
            if primary_key:
                try:
                    cursor.execute(f'DELETE FROM {table_name} WHERE {primary_key} = ?', (record_id,))
                    conn.commit()
                    conn.close()
                    return jsonify({
                        'success': True,
                        'message': '数据删除成功'
                    })
                except sqlite3.OperationalError as e:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'数据删除失败: {str(e)}'
                    }), 400
            else:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': '无法找到表的主键'
                }), 400
        
        conn.close()
        return jsonify({
            'success': False,
            'message': '无效的操作'
        }), 400
        
    except Exception as e:
        print(f"数据管理操作失败: {e}")
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500

# 获取航路数据API端点
@db_view_bp.route('/api/routes/details')
def get_routes_details():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 构建复杂的SQL查询，关联多个表
        cursor.execute('''
            SELECT 
                r.RouteID,
                r.RouteName,
                sw.Name AS StartWaypointName,
                ew.Name AS EndWaypointName,
                r.RouteType,
                r.TotalDistanceKM,
                MIN(rs.MinAltitude) AS MinAltitude,
                MAX(rsm.SequenceNumber) AS SegmentCount,
                r.CreatedAt,
                r.UpdatedAt
            FROM 
                Route r
            LEFT JOIN 
                Waypoint sw ON r.StartWaypointID = sw.WaypointID
            LEFT JOIN 
                Waypoint ew ON r.EndWaypointID = ew.WaypointID
            LEFT JOIN 
                RouteSegmentMapping rsm ON r.RouteID = rsm.RouteID
            LEFT JOIN 
                RouteSegment rs ON rsm.SegmentID = rs.SegmentID
            GROUP BY 
                r.RouteID, r.RouteName, sw.Name, ew.Name, r.RouteType, r.TotalDistanceKM, r.CreatedAt, r.UpdatedAt
            ORDER BY 
                r.RouteID
        ''')
        
        routes = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        route_list = []
        for i, route in enumerate(routes, 1):
            # 处理可能的空值
            route_data = {
                '序号': i,
                'RouteID': route[0],
                '航路名': route[1] if route[1] is not None else '',
                '起点': route[2] if route[2] is not None else '',
                '终点': route[3] if route[3] is not None else '',
                '航路类型': '国内' if route[4] == 'DOMESTIC' else '国外' if route[4] == 'FOREIGN' else '',
                '总距离': route[5] if route[5] is not None else '',
                '最低飞行高（KM）': route[6] if route[6] is not None else '',
                '航段数量': route[7] if route[7] is not None else 0,
                '创建时间': route[8] if route[8] is not None else '',
                '维护时间': route[9] if route[9] is not None else ''
            }
            route_list.append(route_data)
        
        return jsonify({
            'success': True,
            'routes': route_list
        })
    except Exception as e:
        print(f"获取航路数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取航路数据失败: {str(e)}'
        })

# 增加航路点数据API端点
@db_view_bp.route('/api/waypoints/add', methods=['POST'])
def add_waypoint_api():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = request.get_json()
        if not data:
            conn.close()
            return jsonify({
                'success': False,
                'message': '未提供数据'
            }), 400
        
        # 插入航路点数据
        cursor.execute('''
            INSERT INTO Waypoint (Name, Latitude, Longitude, IsActive, CreatedAt, UpdatedAt)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (data.get('Name'), data.get('Latitude'), data.get('Longitude'), data.get('IsActive')))
        
        waypoint_id = cursor.lastrowid
        
        # 处理航路点类型
        if 'TypeCode' in data and 'TypeName' in data:
            # 检查类型是否存在
            cursor.execute('SELECT TypeID FROM WaypointType WHERE TypeCode = ?', (data.get('TypeCode'),))
            type_id = cursor.fetchone()
            
            if not type_id:
                # 插入新类型
                cursor.execute('INSERT INTO WaypointType (TypeCode, TypeName) VALUES (?, ?)', 
                              (data.get('TypeCode'), data.get('TypeName')))
                type_id = cursor.lastrowid
            else:
                type_id = type_id[0]
            
            # 插入类型映射
            cursor.execute('INSERT INTO WaypointTypeMapping (WaypointID, TypeID) VALUES (?, ?)', 
                          (waypoint_id, type_id))
        
        # 处理导航设备信息
        if 'Frequency' in data:
            cursor.execute('INSERT INTO NavaidInfo (WaypointID, Frequency) VALUES (?, ?)', 
                          (waypoint_id, data.get('Frequency')))
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            after_value = {
                'Name': data.get('Name'),
                'Latitude': data.get('Latitude'),
                'Longitude': data.get('Longitude'),
                'IsActive': data.get('IsActive'),
                'TypeCode': data.get('TypeCode'),
                'TypeName': data.get('TypeName'),
                'Frequency': data.get('Frequency')
            }
            record_change_log(
                session['username'],
                '添加',
                'Waypoint',
                waypoint_id,
                '{}',
                json.dumps(after_value),
                '通过前端界面添加航路点'
            )
        
        return jsonify({
            'success': True,
            'message': '航路点添加成功'
        })
    except Exception as e:
        print(f"添加航路点失败: {e}")
        return jsonify({
            'success': False,
            'message': f'添加航路点失败: {str(e)}'
        }), 500

# 修改航路点数据API端点
@db_view_bp.route('/api/waypoints/edit/<id>', methods=['POST'])
def edit_waypoint_api(id):
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = request.get_json()
        if not data:
            conn.close()
            return jsonify({
                'success': False,
                'message': '未提供数据'
            }), 400
        
        # 获取修改前的数据
        cursor.execute('SELECT * FROM Waypoint WHERE WaypointID = ?', (id,))
        old_waypoint = cursor.fetchone()
        old_data = {}
        if old_waypoint:
            old_data = {
                'Name': old_waypoint[1],
                'Latitude': old_waypoint[2],
                'Longitude': old_waypoint[3],
                'IsActive': old_waypoint[4]
            }
        
        # 获取旧的类型信息
        cursor.execute('''
            SELECT wt.TypeCode, wt.TypeName 
            FROM WaypointTypeMapping wtm 
            JOIN WaypointType wt ON wtm.TypeID = wt.TypeID 
            WHERE wtm.WaypointID = ?
        ''', (id,))
        old_type = cursor.fetchone()
        if old_type:
            old_data['TypeCode'] = old_type[0]
            old_data['TypeName'] = old_type[1]
        
        # 获取旧的频率信息
        cursor.execute('SELECT Frequency FROM NavaidInfo WHERE WaypointID = ?', (id,))
        old_freq = cursor.fetchone()
        if old_freq:
            old_data['Frequency'] = old_freq[0]
        
        # 更新航路点数据
        cursor.execute('''
            UPDATE Waypoint
            SET Name = ?, Latitude = ?, Longitude = ?, IsActive = ?, UpdatedAt = CURRENT_TIMESTAMP
            WHERE WaypointID = ?
        ''', (data.get('Name'), data.get('Latitude'), data.get('Longitude'), data.get('IsActive'), id))
        
        # 处理航路点类型
        if 'TypeCode' in data and 'TypeName' in data:
            # 检查类型是否存在
            cursor.execute('SELECT TypeID FROM WaypointType WHERE TypeCode = ?', (data.get('TypeCode'),))
            type_id = cursor.fetchone()
            
            if not type_id:
                # 插入新类型
                cursor.execute('INSERT INTO WaypointType (TypeCode, TypeName) VALUES (?, ?)', 
                              (data.get('TypeCode'), data.get('TypeName')))
                type_id = cursor.lastrowid
            else:
                type_id = type_id[0]
            
            # 删除旧的类型映射
            cursor.execute('DELETE FROM WaypointTypeMapping WHERE WaypointID = ?', (id,))
            
            # 插入新的类型映射
            cursor.execute('INSERT INTO WaypointTypeMapping (WaypointID, TypeID) VALUES (?, ?)', 
                          (id, type_id))
        
        # 处理导航设备信息
        if 'Frequency' in data:
            # 检查是否存在
            cursor.execute('SELECT NavaidID FROM NavaidInfo WHERE WaypointID = ?', (id,))
            if cursor.fetchone():
                # 更新
                cursor.execute('UPDATE NavaidInfo SET Frequency = ? WHERE WaypointID = ?', 
                              (data.get('Frequency'), id))
            else:
                # 插入
                cursor.execute('INSERT INTO NavaidInfo (WaypointID, Frequency) VALUES (?, ?)', 
                              (id, data.get('Frequency')))
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            after_value = {
                'Name': data.get('Name'),
                'Latitude': data.get('Latitude'),
                'Longitude': data.get('Longitude'),
                'IsActive': data.get('IsActive'),
                'TypeCode': data.get('TypeCode'),
                'TypeName': data.get('TypeName'),
                'Frequency': data.get('Frequency')
            }
            record_change_log(
                session['username'],
                '修改',
                'Waypoint',
                id,
                json.dumps(old_data),
                json.dumps(after_value),
                '通过前端界面修改航路点'
            )
        
        return jsonify({
            'success': True,
            'message': '航路点修改成功'
        })
    except Exception as e:
        print(f"修改航路点失败: {e}")
        return jsonify({
            'success': False,
            'message': f'修改航路点失败: {str(e)}'
        }), 500

# 删除航路点数据API端点
@db_view_bp.route('/api/waypoints/delete/<id>', methods=['POST'])
def delete_waypoint_api(id):
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取删除前的数据
        cursor.execute('SELECT * FROM Waypoint WHERE WaypointID = ?', (id,))
        old_waypoint = cursor.fetchone()
        old_data = {}
        if old_waypoint:
            old_data = {
                'Name': old_waypoint[1],
                'Latitude': old_waypoint[2],
                'Longitude': old_waypoint[3],
                'IsActive': old_waypoint[4]
            }
        
        # 获取旧的类型信息
        cursor.execute('''
            SELECT wt.TypeCode, wt.TypeName 
            FROM WaypointTypeMapping wtm 
            JOIN WaypointType wt ON wtm.TypeID = wt.TypeID 
            WHERE wtm.WaypointID = ?
        ''', (id,))
        old_type = cursor.fetchone()
        if old_type:
            old_data['TypeCode'] = old_type[0]
            old_data['TypeName'] = old_type[1]
        
        # 获取旧的频率信息
        cursor.execute('SELECT Frequency FROM NavaidInfo WHERE WaypointID = ?', (id,))
        old_freq = cursor.fetchone()
        if old_freq:
            old_data['Frequency'] = old_freq[0]
        
        # 删除相关数据
        cursor.execute('DELETE FROM NavaidInfo WHERE WaypointID = ?', (id,))
        cursor.execute('DELETE FROM WaypointTypeMapping WHERE WaypointID = ?', (id,))
        cursor.execute('DELETE FROM Waypoint WHERE WaypointID = ?', (id,))
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            record_change_log(
                session['username'],
                '删除',
                'Waypoint',
                id,
                json.dumps(old_data),
                '{}',
                '通过前端界面删除航路点'
            )
        
        return jsonify({
            'success': True,
            'message': '航路点删除成功'
        })
    except Exception as e:
        print(f"删除航路点失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除航路点失败: {str(e)}'
        }), 500

# 查询航路点数据API端点
@db_view_bp.route('/api/waypoints/search', methods=['GET'])
def search_waypoints_api():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        keyword = request.args.get('keyword', '')
        
        # 构建搜索查询
        cursor.execute('''
            SELECT 
                w.WaypointID,
                w.Name,
                w.Latitude,
                w.Longitude,
                w.IsActive,
                wt.TypeCode,
                wt.TypeName,
                n.Frequency,
                w.CreatedAt,
                w.UpdatedAt
            FROM 
                Waypoint w
            LEFT JOIN 
                WaypointTypeMapping wtm ON w.WaypointID = wtm.WaypointID
            LEFT JOIN 
                WaypointType wt ON wtm.TypeID = wt.TypeID
            LEFT JOIN 
                NavaidInfo n ON w.WaypointID = n.WaypointID
            WHERE 
                w.Name LIKE ? OR
                wt.TypeCode LIKE ? OR
                wt.TypeName LIKE ?
            ORDER BY 
                w.WaypointID
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        
        waypoints = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        waypoint_list = []
        for i, wp in enumerate(waypoints, 1):
            waypoint_data = {
                '序号': i,
                'WaypointID': wp[0],
                '点名称': wp[1] if wp[1] is not None else '',
                '纬度': wp[2] if wp[2] is not None else '',
                '经度': wp[3] if wp[3] is not None else '',
                '状态': '有效' if wp[4] == 1 else '停用',
                '点类型': wp[5] if wp[5] is not None else '',
                '类型名称': wp[6] if wp[6] is not None else '',
                '频率': wp[7] if wp[7] is not None else '',
                '创建时间': wp[8] if wp[8] is not None else '',
                '维护时间': wp[9] if wp[9] is not None else ''
            }
            waypoint_list.append(waypoint_data)
        
        return jsonify({
            'success': True,
            'waypoints': waypoint_list
        })
    except Exception as e:
        print(f"搜索航路点失败: {e}")
        return jsonify({
            'success': False,
            'message': f'搜索航路点失败: {str(e)}'
        }), 500

# 增加航路数据API端点
@db_view_bp.route('/api/routes/add', methods=['POST'])
def add_route_api():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = request.get_json()
        if not data:
            conn.close()
            return jsonify({
                'success': False,
                'message': '未提供数据'
            }), 400
        
        # 插入航路数据
        cursor.execute('''
            INSERT INTO Route (RouteName, StartWaypointID, EndWaypointID, RouteType, TotalDistanceKM, CreatedAt, UpdatedAt)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (data.get('RouteName'), 1, 1, data.get('RouteType'), data.get('TotalDistanceKM')))
        
        route_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            after_value = {
                'RouteName': data.get('RouteName'),
                'RouteType': data.get('RouteType'),
                'TotalDistanceKM': data.get('TotalDistanceKM')
            }
            record_change_log(
                session['username'],
                '添加',
                'Route',
                route_id,
                '{}',
                json.dumps(after_value),
                '通过前端界面添加航路'
            )
        
        return jsonify({
            'success': True,
            'message': '航路添加成功'
        })
    except Exception as e:
        print(f"添加航路失败: {e}")
        return jsonify({
            'success': False,
            'message': f'添加航路失败: {str(e)}'
        }), 500

# 修改航路数据API端点
@db_view_bp.route('/api/routes/edit/<id>', methods=['POST'])
def edit_route_api(id):
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = request.get_json()
        if not data:
            conn.close()
            return jsonify({
                'success': False,
                'message': '未提供数据'
            }), 400
        
        # 获取修改前的数据
        cursor.execute('SELECT * FROM Route WHERE RouteID = ?', (id,))
        old_route = cursor.fetchone()
        old_data = {}
        if old_route:
            old_data = {
                'RouteName': old_route[1],
                'RouteType': old_route[4],
                'TotalDistanceKM': old_route[5]
            }
        
        # 更新航路数据
        cursor.execute('''
            UPDATE Route
            SET RouteName = ?, RouteType = ?, TotalDistanceKM = ?, UpdatedAt = CURRENT_TIMESTAMP
            WHERE RouteID = ?
        ''', (data.get('RouteName'), data.get('RouteType'), data.get('TotalDistanceKM'), id))
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            after_value = {
                'RouteName': data.get('RouteName'),
                'RouteType': data.get('RouteType'),
                'TotalDistanceKM': data.get('TotalDistanceKM')
            }
            record_change_log(
                session['username'],
                '修改',
                'Route',
                id,
                json.dumps(old_data),
                json.dumps(after_value),
                '通过前端界面修改航路'
            )
        
        return jsonify({
            'success': True,
            'message': '航路修改成功'
        })
    except Exception as e:
        print(f"修改航路失败: {e}")
        return jsonify({
            'success': False,
            'message': f'修改航路失败: {str(e)}'
        }), 500

# 删除航路数据API端点
@db_view_bp.route('/api/routes/delete/<id>', methods=['POST'])
def delete_route_api(id):
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取删除前的数据
        cursor.execute('SELECT * FROM Route WHERE RouteID = ?', (id,))
        old_route = cursor.fetchone()
        old_data = {}
        if old_route:
            old_data = {
                'RouteName': old_route[1],
                'RouteType': old_route[4],
                'TotalDistanceKM': old_route[5]
            }
        
        # 删除相关数据
        cursor.execute('DELETE FROM RouteSegmentMapping WHERE RouteID = ?', (id,))
        cursor.execute('DELETE FROM Route WHERE RouteID = ?', (id,))
        
        conn.commit()
        conn.close()
        
        # 记录变更日志
        if 'username' in session:
            record_change_log(
                session['username'],
                '删除',
                'Route',
                id,
                json.dumps(old_data),
                '{}',
                '通过前端界面删除航路'
            )
        
        return jsonify({
            'success': True,
            'message': '航路删除成功'
        })
    except Exception as e:
        print(f"删除航路失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除航路失败: {str(e)}'
        }), 500

# 查询航路数据API端点
@db_view_bp.route('/api/routes/search', methods=['GET'])
def search_routes_api():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        keyword = request.args.get('keyword', '')
        
        # 构建搜索查询
        cursor.execute('''
            SELECT 
                r.RouteID,
                r.RouteName,
                sw.Name AS StartWaypointName,
                ew.Name AS EndWaypointName,
                r.RouteType,
                r.TotalDistanceKM,
                MIN(rs.MinAltitude) AS MinAltitude,
                MAX(rsm.SequenceNumber) AS SegmentCount,
                r.CreatedAt,
                r.UpdatedAt
            FROM 
                Route r
            LEFT JOIN 
                Waypoint sw ON r.StartWaypointID = sw.WaypointID
            LEFT JOIN 
                Waypoint ew ON r.EndWaypointID = ew.WaypointID
            LEFT JOIN 
                RouteSegmentMapping rsm ON r.RouteID = rsm.RouteID
            LEFT JOIN 
                RouteSegment rs ON rsm.SegmentID = rs.SegmentID
            WHERE 
                r.RouteName LIKE ?
            GROUP BY 
                r.RouteID, r.RouteName, sw.Name, ew.Name, r.RouteType, r.TotalDistanceKM, r.CreatedAt, r.UpdatedAt
            ORDER BY 
                r.RouteID
        ''', (f'%{keyword}%',))
        
        routes = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        route_list = []
        for i, route in enumerate(routes, 1):
            route_data = {
                '序号': i,
                'RouteID': route[0],
                '航路名': route[1] if route[1] is not None else '',
                '起点': route[2] if route[2] is not None else '',
                '终点': route[3] if route[3] is not None else '',
                '航路类型': '国内' if route[4] == 'DOMESTIC' else '国外' if route[4] == 'FOREIGN' else '',
                '总距离': route[5] if route[5] is not None else '',
                '最低飞行高（KM）': route[6] if route[6] is not None else '',
                '航段数量': route[7] if route[7] is not None else 0,
                '创建时间': route[8] if route[8] is not None else '',
                '维护时间': route[9] if route[9] is not None else ''
            }
            route_list.append(route_data)
        
        return jsonify({
            'success': True,
            'routes': route_list
        })
    except Exception as e:
        print(f"搜索航路失败: {e}")
        return jsonify({
            'success': False,
            'message': f'搜索航路失败: {str(e)}'
        }), 500
