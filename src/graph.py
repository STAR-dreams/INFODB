from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
import sqlite3
import os
import json
import sys
from datetime import datetime

# 创建蓝图
graph_bp = Blueprint('graph', __name__)

# 获取程序运行目录（exe文件所在目录）
if hasattr(sys, '_MEIPASS'):
    # 打包后的环境
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 开发环境
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 数据库路径
INFO_DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
USER_DB_PATH = os.path.join(BASE_DIR, 'db', 'user.sqlite')

# 登录检查装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 图形编辑页面
@graph_bp.route('/graph_redact')
@login_required
def graph_redact_page():
    return render_template('graph_redact.html')

# 获取航路列表API端点
@graph_bp.route('/api/routes/list')
@login_required
def get_routes_list():
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        
        # 查询所有航路
        cursor.execute('''
            SELECT RouteID, RouteName 
            FROM Route 
            ORDER BY RouteName
        ''')
        
        routes = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        route_list = [{'id': route[0], 'name': route[1]} for route in routes]
        
        return jsonify({
            'success': True,
            'routes': route_list
        })
    except Exception as e:
        print(f"获取航路列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取航路列表失败'
        })

# 获取所有航路详细信息API端点
@graph_bp.route('/api/routes')
@login_required
def get_all_routes():
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        
        # 查询所有航路基本信息
        cursor.execute('''
            SELECT RouteID, RouteName, RouteType, StartWaypointID, EndWaypointID, TotalDistanceKM
            FROM Route 
            ORDER BY RouteName
        ''')
        
        routes = cursor.fetchall()
        
        # 准备返回数据
        result_routes = []
        
        for route in routes:
            route_id = route[0]
            
            # 查询起始和结束航点的名称
            cursor.execute('''
                SELECT sw.Name AS StartWaypointName, ew.Name AS EndWaypointName
                FROM Waypoint sw, Waypoint ew
                WHERE sw.WaypointID = ? AND ew.WaypointID = ?
            ''', (route[3], route[4]))
            
            waypoint_names = cursor.fetchone()
            start_waypoint_name = waypoint_names[0] if waypoint_names else ""
            end_waypoint_name = waypoint_names[1] if waypoint_names else ""
            
            # 查询该航路的所有航段
            cursor.execute('''
                SELECT rs.SegmentID, rs.StartWaypointID, rs.EndWaypointID, rs.DistanceKM, 
                       rs.Direction, rs.MinAltitude, rs.SegmentType, rs.IsBidirectional,
                       rsm.SequenceNumber, rsm.IsReversed,
                       sw.Name AS StartName, ew.Name AS EndName,
                       sw.Latitude AS StartLatitude, sw.Longitude AS StartLongitude,
                       ew.Latitude AS EndLatitude, ew.Longitude AS EndLongitude
                FROM RouteSegmentMapping rsm
                JOIN RouteSegment rs ON rsm.SegmentID = rs.SegmentID
                JOIN Waypoint sw ON rs.StartWaypointID = sw.WaypointID
                JOIN Waypoint ew ON rs.EndWaypointID = ew.WaypointID
                WHERE rsm.RouteID = ?
                ORDER BY rsm.SequenceNumber
            ''', (route_id,))
            
            segments = cursor.fetchall()
            
            # 格式化航段数据
            formatted_segments = []
            for seg in segments:
                formatted_segments.append({
                    'SegmentID': seg[0],
                    'StartWaypointID': seg[1],
                    'EndWaypointID': seg[2],
                    'DistanceKM': seg[3],
                    'Direction': seg[4],
                    'MinAltitude': seg[5],
                    'SegmentType': seg[6],
                    'IsBidirectional': seg[7],
                    'SequenceNumber': seg[8],
                    'IsReversed': seg[9],
                    'StartName': seg[10],
                    'EndName': seg[11],
                    'StartLatitude': seg[12],
                    'StartLongitude': seg[13],
                    'EndLatitude': seg[14],
                    'EndLongitude': seg[15]
                })
            
            # 添加到结果列表
            result_routes.append({
                'RouteID': route[0],
                'RouteName': route[1],
                'RouteType': route[2],
                'StartWaypointID': route[3],
                'EndWaypointID': route[4],
                'TotalDistanceKM': route[5],
                'StartWaypointName': start_waypoint_name,
                'EndWaypointName': end_waypoint_name,
                'Segments': formatted_segments
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'routes': result_routes
        })
    except Exception as e:
        print(f"获取所有航路失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取所有航路失败'
        })

# 保存航线API端点
@graph_bp.route('/graph/api/save-route', methods=['POST'])
@login_required
def save_route():
    try:
        # 获取请求数据
        route_data = request.json
        
        # 确保编辑数据目录存在
        edit_data_dir = 'edit_data'
        os.makedirs(edit_data_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        route_name = route_data.get('name', 'unnamed').replace(' ', '_')
        filename = f"{route_name}_{timestamp}.json"
        file_path = os.path.join(edit_data_dir, filename)
        
        # 保存为JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(route_data, f, ensure_ascii=False, indent=2)
        
        # 可选：将航线数据保存到数据库
        # save_route_to_database(route_data)
        
        return jsonify({
            'success': True,
            'message': '航线保存成功',
            'file_path': file_path
        })
    except Exception as e:
        print(f"保存航线失败: {e}")
        return jsonify({
            'success': False,
            'message': f'保存航线失败: {str(e)}'
        })

# 可选：将航线数据保存到数据库
def save_route_to_database(route_data):
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        
        # 开始事务
        conn.execute('BEGIN TRANSACTION')
        
        # 插入Route表
        cursor.execute('''
            INSERT INTO Route (RouteName, RouteType, StartWaypointID, EndWaypointID, TotalDistanceKM)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            route_data['name'],
            'DOMESTIC',  # 默认类型
            route_data['waypoints'][0]['waypointId'],
            route_data['waypoints'][-1]['waypointId'],
            0  # 距离将在后续计算
        ))
        
        route_id = cursor.lastrowid
        
        # 计算总距离并更新
        total_distance = calculate_route_distance(route_data['waypoints'])
        cursor.execute('''
            UPDATE Route SET TotalDistanceKM = ? WHERE RouteID = ?
        ''', (total_distance, route_id))
        
        # 提交事务
        conn.commit()
        conn.close()
        
        return route_id
    except Exception as e:
        print(f"保存航线到数据库失败: {e}")
        conn.rollback()
        conn.close()
        return None

# 获取航路详细信息API端点
@graph_bp.route('/api/route/<int:route_id>')
@login_required
def get_route_details(route_id):
    try:
        conn = sqlite3.connect(INFO_DB_PATH)
        cursor = conn.cursor()
        
        # 查询航路基本信息
        cursor.execute('''
            SELECT RouteID, RouteName, RouteType, StartWaypointID, EndWaypointID, TotalDistanceKM
            FROM Route 
            WHERE RouteID = ?
        ''', (route_id,))
        
        route = cursor.fetchone()
        if not route:
            conn.close()
            return jsonify({
                'success': False,
                'message': '航路不存在'
            })
        
        # 查询起始和结束航点的名称
        cursor.execute('''
            SELECT sw.Name AS StartWaypointName, ew.Name AS EndWaypointName
            FROM Waypoint sw, Waypoint ew
            WHERE sw.WaypointID = ? AND ew.WaypointID = ?
        ''', (route[3], route[4]))
        
        waypoint_names = cursor.fetchone()
        start_waypoint_name = waypoint_names[0] if waypoint_names else ""
        end_waypoint_name = waypoint_names[1] if waypoint_names else ""
        
        # 查询该航路的所有航段
        cursor.execute('''
            SELECT rs.SegmentID, rs.StartWaypointID, rs.EndWaypointID, rs.DistanceKM, 
                   rs.Direction, rs.MinAltitude, rs.SegmentType, rs.IsBidirectional,
                   rsm.SequenceNumber, rsm.IsReversed,
                   sw.Name AS StartName, ew.Name AS EndName,
                   sw.Latitude AS StartLatitude, sw.Longitude AS StartLongitude,
                   ew.Latitude AS EndLatitude, ew.Longitude AS EndLongitude
            FROM RouteSegmentMapping rsm
            JOIN RouteSegment rs ON rsm.SegmentID = rs.SegmentID
            JOIN Waypoint sw ON rs.StartWaypointID = sw.WaypointID
            JOIN Waypoint ew ON rs.EndWaypointID = ew.WaypointID
            WHERE rsm.RouteID = ?
            ORDER BY rsm.SequenceNumber
        ''', (route_id,))
        
        segments = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                'SegmentID': seg[0],
                'StartWaypointID': seg[1],
                'EndWaypointID': seg[2],
                'DistanceKM': seg[3],
                'Direction': seg[4],
                'MinAltitude': seg[5],
                'SegmentType': seg[6],
                'IsBidirectional': seg[7],
                'SequenceNumber': seg[8],
                'IsReversed': seg[9],
                'StartName': seg[10],
                'EndName': seg[11],
                'StartLatitude': seg[12],
                'StartLongitude': seg[13],
                'EndLatitude': seg[14],
                'EndLongitude': seg[15]
            })
        
        return jsonify({
            'success': True,
            'route': {
                'RouteID': route[0],
                'RouteName': route[1],
                'RouteType': route[2],
                'StartWaypointID': route[3],
                'EndWaypointID': route[4],
                'TotalDistanceKM': route[5],
                'StartWaypointName': start_waypoint_name,
                'EndWaypointName': end_waypoint_name,
                'Segments': formatted_segments
            }
        })
    except Exception as e:
        print(f"获取航路详细信息失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取航路详细信息失败'
        })
