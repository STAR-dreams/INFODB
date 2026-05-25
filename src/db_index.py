from flask import Blueprint, jsonify, render_template, session, redirect, url_for
import sqlite3
import os

# 创建蓝图
db_index_bp = Blueprint('db_index', __name__)

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

# 登录检查装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 执行SQL查询
def execute_query(query, params=()):
    # 确保数据库文件所在目录存在
    os.makedirs(os.path.dirname(INFO_DB_PATH), exist_ok=True)
    
    # 尝试以可写模式打开数据库
    conn = sqlite3.connect(INFO_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

# 获取航路统计数据
@db_index_bp.route('/api/route-stats')
@login_required
def get_route_stats():
    try:
        # 获取航路总数
        total_routes = execute_query("SELECT COUNT(*) FROM Route")[0][0]
        
        # 获取国内航路数量
        domestic_routes = execute_query("SELECT COUNT(*) FROM Route WHERE RouteType = 'DOMESTIC'")[0][0]
        
        # 获取国外航路数量
        foreign_routes = execute_query("SELECT COUNT(*) FROM Route WHERE RouteType = 'FOREIGN'")[0][0]
        
        # 获取平均航路距离
        avg_distance = execute_query("SELECT AVG(TotalDistanceKM) FROM Route")[0][0] or 0
        
        # 获取航路类型分布
        route_type_distribution = [
            {"name": "国内", "value": domestic_routes},
            {"name": "国外", "value": foreign_routes}
        ]
        
        # 获取航路段数统计
        route_segment_count = execute_query("""
            SELECT r.RouteID, r.RouteName, r.RouteType, COUNT(rsm.SegmentID) as segment_count
            FROM Route r
            LEFT JOIN RouteSegmentMapping rsm ON r.RouteID = rsm.RouteID
            GROUP BY r.RouteID
            ORDER BY segment_count DESC
            LIMIT 10
        """)
        
        route_segment_data = []
        for route in route_segment_count:
            route_segment_data.append({
                "route_name": route["RouteName"],
                "segment_count": route["segment_count"],
                "route_type": "国内" if route["RouteType"] == "DOMESTIC" else "国外"
            })
        
        # 获取双向/单向航段统计
        bidirectional_segments = execute_query("SELECT COUNT(*) FROM RouteSegmentMapping WHERE IsReversed = 1")[0][0]
        unidirectional_segments = execute_query("SELECT COUNT(*) FROM RouteSegmentMapping WHERE IsReversed = 0")[0][0]
        
        segment_direction_data = [
            {"name": "双向航段", "value": bidirectional_segments},
            {"name": "单向航段", "value": unidirectional_segments}
        ]
        
        return jsonify({
            "success": True,
            "data": {
                "total_routes": total_routes,
                "domestic_routes": domestic_routes,
                "foreign_routes": foreign_routes,
                "avg_distance": round(avg_distance, 2),
                "route_type_distribution": route_type_distribution,
                "route_segment_data": route_segment_data,
                "segment_direction_data": segment_direction_data
            }
        })
    except Exception as e:
        print(f"获取航路统计数据失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取数据失败: {str(e)}"
        })

# 获取航段统计数据
@db_index_bp.route('/api/segment-stats')
@login_required
def get_segment_stats():
    try:
        # 获取航段总数
        total_segments = execute_query("SELECT COUNT(*) FROM RouteSegment")[0][0]
        
        # 获取平均航段距离
        avg_segment_distance = execute_query("SELECT AVG(DistanceKM) FROM RouteSegment")[0][0] or 0
        
        # 获取最长和最短航段
        longest_segment = execute_query("SELECT MAX(DistanceKM) FROM RouteSegment")[0][0] or 0
        shortest_segment = execute_query("SELECT MIN(DistanceKM) FROM RouteSegment WHERE DistanceKM > 0")[0][0] or 0
        
        return jsonify({
            "success": True,
            "data": {
                "total_segments": total_segments,
                "avg_segment_distance": round(avg_segment_distance, 2),
                "longest_segment": round(longest_segment, 2),
                "shortest_segment": round(shortest_segment, 2)
            }
        })
    except Exception as e:
        print(f"获取航段统计数据失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取数据失败: {str(e)}"
        })