# 数字化航图平台项目说明文档

提供航空情报数据管理与地图可视化平台，便于航图编辑与审计。

[回到README](../README.md)

## 1. 项目概述

数字化航图平台是一个基于 Flask 框架开发的航空情报数据管理与可视化系统，旨在为航空领域提供高效、直观的数据管理和地图可视化功能。

### 1.1 主要功能

- **用户认证与管理**：支持用户登录、注册和权限控制
- **航空情报数据管理**：对航路点、导航台、航段、航路等数据进行CRUD操作
- **地图可视化**：基于Leaflet.js实现交互式地图显示和数据可视化
- **航路编辑**：支持在地图上创建、修改和删除航路
- **实时日志记录**：记录所有用户操作和数据变更
- **API接口**：提供完整的数据查询和操作接口

### 1.2 技术栈

- **后端**：Flask + SQLite
- **前端**：HTML + CSS + JavaScript
- **地图库**：Leaflet.js + Leaflet.markercluster
- **数据存储**：SQLite数据库
- **项目结构**：模块化设计，使用Flask蓝图组织代码

## 2. 项目结构

### 2.1 目录结构

```
INFODB/
├── db/                     # 数据库文件
│   ├── info.sqlite         # 航空情报数据
│   ├── user.sqlite         # 用户数据
├── static/             # 网页静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── scripts.js
├── templates/              # HTML模板
│   ├── base.html           # 基础模板
│   ├── dashboard.html      # 登录主控界面
│   ├── data_manage.html    # 数据管理界面
│   ├── database_view.html  # 数据库视图创建
│   ├── login.html          # 登录界面
│   ├── register.html       # 注册界面
│   ├── user_manage.html    # 用户管理
│   ├── database_view.html  # 数据管理页面
│   ├── graph_redact.html   # 航路编辑页面
│   └── draw.html           # 地图显示页面
├── edit_data/              # 编辑数据存储
├── img/                    # 图片资源
├── infodbVenv/             # 虚拟环境
├── main.py                 # 主应用文件
├── db_view.py              # 数据管理模块
├── graph.py                # 地图功能模块
└── db_index.py             # 数据库索引模块
```

### 2.2 核心文件说明

| 文件名称 | 主要功能 | 位置 |
|---------|---------|------|
| main.py | 主应用配置、用户认证、路由管理 | 项目根目录 |
| db_view.py | 数据管理、API接口、变更日志记录 | 项目根目录 |
| graph.py | 地图功能、航路编辑、路由管理 | 项目根目录 |
| db_index.py | 数据库索引、查询优化 | 项目根目录 |
| database_view.html | 数据管理前端界面 | templates/ |
| graph_redact.html | 航路编辑前端界面 | templates/ |
| draw.html | 地图显示前端界面 | templates/ |

## 3. 系统功能模块

### 3.1 用户认证与管理

#### 3.1.1 功能描述
- 用户登录、注册和权限控制
- 默认管理员账户创建
- 用户信息管理（添加、编辑、删除）

#### 3.1.2 核心代码

**初始化用户数据库**
```python
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
```
<mcfile name="main.py" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\main.py"></mcfile>

### 3.2 数据管理模块

#### 3.2.1 功能描述
- 航空情报数据的增删改查
- 数据变更日志记录
- 数据可视化展示
- 支持多表操作

#### 3.2.2 核心代码

**获取航路点数据API**
```python
@db_view_bp.route('/api/waypoints/details')
def get_waypoints_details():
    try:
        # 使用绝对路径连接数据库
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DB_PATH = os.path.join(BASE_DIR, 'db', 'info.sqlite')
        
        conn = sqlite3.connect(DB_PATH)
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
```
<mcfile name="db_view.py" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\db_view.py"></mcfile>

### 3.3 地图可视化模块

#### 3.3.1 功能描述
- 基于Leaflet.js的交互式地图
- 多图层控制（航路点、导航台、航段、航路）
- 标记聚类优化
- 航路编辑功能
- 底图切换

#### 3.3.2 核心代码

**地图初始化**
```javascript
function initMap() {
  // 初始化地图
  map = L.map('map').setView([39.9, 116.4], 12);

  // 定义三个底图
  basemaps.streets = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}', {
    subdomains: '1234',
    attribution: '© 高德地图'
  });

  basemaps.satellite = L.tileLayer('https://webst0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=6&x={x}&y={y}&z={z}', {
    subdomains: '1234',
    attribution: '© 高德地图'
  });

  basemaps.roads = L.tileLayer('https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: '1234',
    attribution: '© 高德地图'
  });

  // 默认加载街道图
  currentBasemap = basemaps.streets;
  currentBasemap.addTo(map);

  // 添加图层到地图
  map.addLayer(waypointLayer);
  map.addLayer(navaidLayer);
  map.addLayer(segmentLayer);
  map.addLayer(routeLayer);
  map.addLayer(editRouteLayer);

  // 加载数据
  loadWaypoints();
  loadNavaids();
  loadSegments();
  loadRoutes();

  // 添加地图点击事件，清除选择框
  map.on('click', function(e) {
      if (currentSegmentSelection) {
          map.removeLayer(currentSegmentSelection);
          currentSegmentSelection = null;
      }
  });

  // 添加缩放事件监听，优化坐标对齐
  map.on('zoomend', debounce(function(e) {
      // 重新渲染图层以确保坐标对齐
      if (waypointLayer) {
          waypointLayer.refreshClusters();
      }
      if (navaidLayer) {
          navaidLayer.refreshClusters();
      }
  }, 100));

  // 绘制多边形和标记
  drawMapElements();
}
```
<mcfile name="graph_redact.html" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\templates\graph_redact.html"></mcfile>

### 3.4 航路编辑模块

#### 3.4.1 功能描述
- 交互式航路创建
- 航路点选择与编辑
- 航路保存与管理
- 编辑状态管理

#### 3.4.2 核心代码

**开始编辑模式**
```javascript
function startEditMode() {
    editMode = true;
    selectedWaypoints = [];
    if (editLine) {
        map.removeLayer(editLine);
        editLine = null;
    }
    
    // 更新UI
    document.getElementById('cancelEditBtn').style.display = 'block';
    document.getElementById('editStatus').textContent = '编辑状态：已开始（点击选择点，双击结束）';
    map.getContainer().style.cursor = 'crosshair';
    
    // 添加双击事件结束编辑
    map.on('dblclick', endEditMode);
}
```
<mcfile name="graph_redact.html" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\templates\graph_redact.html"></mcfile>

**保存航线**
```javascript
function saveRoute(routeData) {
    // 发送数据到后端
    fetch('/graph/api/save-route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(routeData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('航线保存成功！');
            // 可以在这里添加新保存的航线到地图
            addSavedRouteToMap(routeData);
        } else {
            alert('航线保存失败：' + data.message);
        }
    })
    .catch(error => {
        console.error('保存航线失败:', error);
        alert('保存航线失败，请重试');
    });
}
```
<mcfile name="graph_redact.html" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\templates\graph_redact.html"></mcfile>

### 3.5 变更日志模块

#### 3.5.1 功能描述
- 记录所有数据变更操作
- 跟踪用户操作历史
- 支持变更查询和审计

#### 3.5.2 核心代码

**记录变更日志**
```python
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
```
<mcfile name="main.py" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\main.py"></mcfile>

## 4. 前端界面设计

### 4.1 数据管理页面

#### 4.1.1 功能描述
- 表格形式展示航空情报数据
- 支持数据筛选和搜索
- 提供数据编辑、删除、添加功能
- 实时显示操作日志

#### 4.1.2 界面布局
- 顶部导航栏：包含系统标题和导航菜单
- 左侧工具栏：提供数据管理功能入口
- 主内容区：数据表格展示
- 右侧日志面板：显示操作日志

### 4.2 地图可视化页面

#### 4.2.1 功能描述
- 交互式地图显示
- 多图层控制
- 底图切换
- 数据点可视化

#### 4.2.2 界面布局
- 顶部控制栏：包含底图选择和操作按钮
- 主地图区：显示地图和数据
- 右侧图层控制面板：控制各图层的显示/隐藏
- 左侧边栏：提供航路编辑功能（默认折叠）

### 4.3 航路编辑页面

#### 4.3.1 功能描述
- 交互式航路创建和编辑
- 航路点选择和管理
- 航路保存和加载
- 编辑状态管理

#### 4.3.2 界面布局
- 顶部控制栏：包含底图选择和操作按钮
- 主地图区：显示地图和航路
- 左侧编辑面板：提供航路编辑工具（默认折叠）
- 右侧图层控制面板：控制各图层的显示/隐藏

### 4.4 数据可视化实现方式

#### 4.4.1 数据获取与统计
前端通过以下方式获取和统计数据库数据：

1. **API数据获取**：
   - 使用Fetch API从后端API接口获取原始数据
   - 支持的接口包括：`/api/waypoints`、`/api/navaids`、`/api/segments`、`/api/routes`等
   - 数据格式为JSON，包含完整的航空情报信息

2. **前端数据统计**：
   - 使用JavaScript进行客户端数据处理和统计
   - 实现的统计功能包括：
     - 航路点数量统计（按类型、状态分类）
     - 航段距离统计（总距离、平均距离）
     - 航路长度统计（按类型分类）
     - 导航台频率分布统计

3. **数据缓存策略**：
   - 实现前端数据缓存，减少重复API调用
   - 使用localStorage存储临时统计结果
   - 数据更新时自动刷新缓存

#### 4.4.2 图表绘制实现
前端使用以下技术进行数据可视化图表绘制：

1. **地图数据可视化**：
   - 使用Leaflet.js实现交互式地图显示
   - 使用Leaflet.markercluster插件实现标记聚类，优化大量数据点的显示
   - 自定义图标和样式，区分不同类型的数据点
   - 实现数据点的悬停提示和点击详情

2. **统计图表绘制**：
   - 集成Chart.js库实现各种统计图表
   - 支持的图表类型包括：
     - 饼图：用于展示航路点类型分布
     - 柱状图：用于比较不同类型航路的长度
     - 折线图：用于展示航段距离分布
     - 雷达图：用于多维度数据对比

3. **实时数据更新**：
   - 实现图表数据的实时更新机制
   - 当数据库数据发生变化时，自动刷新图表
   - 使用防抖技术优化频繁数据更新的性能

4. **响应式设计**：
   - 图表自适应不同屏幕尺寸
   - 在移动设备上优化显示效果
   - 支持触摸操作和手势控制

#### 4.4.3 核心实现代码

**数据获取与处理**：
```javascript
// 获取航路点数据并进行统计
function loadWaypointsAndStats() {
    fetch('/api/waypoints')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 存储原始数据
                window.waypointData = data.waypoints;
                
                // 进行数据统计
                const stats = {
                    total: data.waypoints.length,
                    byType: {},
                    byStatus: { active: 0, inactive: 0 }
                };
                
                // 按类型和状态统计
                data.waypoints.forEach(waypoint => {
                    // 按类型统计
                    if (waypoint.type) {
                        if (!stats.byType[waypoint.type]) {
                            stats.byType[waypoint.type] = 0;
                        }
                        stats.byType[waypoint.type]++;
                    }
                    
                    // 按状态统计
                    if (waypoint.isActive) {
                        stats.byStatus.active++;
                    } else {
                        stats.byStatus.inactive++;
                    }
                });
                
                // 绘制统计图表
                drawWaypointStats(stats);
            }
        })
        .catch(error => {
            console.error('加载航路点数据失败:', error);
        });
}
```

**图表绘制**：
```javascript
// 绘制航路点统计图表
function drawWaypointStats(stats) {
    // 饼图：航路点类型分布
    const typeCtx = document.getElementById('waypointTypeChart').getContext('2d');
    new Chart(typeCtx, {
        type: 'pie',
        data: {
            labels: Object.keys(stats.byType),
            datasets: [{
                data: Object.values(stats.byType),
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(153, 102, 255, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: '航路点类型分布'
            }
        }
    });
    
    // 柱状图：航路点状态分布
    const statusCtx = document.getElementById('waypointStatusChart').getContext('2d');
    new Chart(statusCtx, {
        type: 'bar',
        data: {
            labels: ['活跃', '非活跃'],
            datasets: [{
                label: '航路点数量',
                data: [stats.byStatus.active, stats.byStatus.inactive],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: '航路点状态分布'
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}
```

## 5. API 接口设计

### 5.1 数据查询接口

| 接口路径 | 方法 | 功能描述 | 参数 | 返回格式 |
|---------|------|---------|------|---------|
| `/api/waypoints` | GET | 获取航路点数据 | 无 | JSON |
| `/api/waypoints/details` | GET | 获取详细航路点数据 | 无 | JSON |
| `/api/navaids` | GET | 获取导航台数据 | 无 | JSON |
| `/api/segments` | GET | 获取航段数据 | 无 | JSON |
| `/api/routes` | GET | 获取航路数据 | 无 | JSON |
| `/api/routes/list` | GET | 获取航路列表 | 无 | JSON |

### 5.2 数据操作接口

| 接口路径 | 方法 | 功能描述 | 参数 | 返回格式 |
|---------|------|---------|------|---------|
| `/graph/api/save-route` | POST | 保存航线 | JSON | JSON |
| `/api/add-waypoint` | POST | 添加航路点 | JSON | JSON |
| `/api/edit-waypoint` | POST | 编辑航路点 | JSON | JSON |
| `/api/delete-waypoint` | POST | 删除航路点 | JSON | JSON |
| `/api/add-route` | POST | 添加航路 | JSON | JSON |
| `/api/edit-route` | POST | 编辑航路 | JSON | JSON |
| `/api/delete-route` | POST | 删除航路 | JSON | JSON |

### 5.3 系统接口

| 接口路径 | 方法 | 功能描述 | 参数 | 返回格式 |
|---------|------|---------|------|---------|
| `/api/access-logs` | GET | 获取访问日志 | 无 | JSON |
| `/api/tables` | GET | 获取数据库表列表 | 无 | JSON |
| `/api/table-structure` | GET | 获取表结构 | table_name | JSON |
| `/api/table-data` | GET | 获取表数据 | table_name, page, per_page, search_term | JSON |

## 6. 技术优化与性能提升

### 6.1 前端性能优化

#### 6.1.1 标记聚类
使用 Leaflet.markercluster 插件对大量标记进行聚类，减少渲染元素数量，提升地图响应速度。

```javascript
let waypointLayer = L.markerClusterGroup({
    maxClusterRadius: 50,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
});
let navaidLayer = L.markerClusterGroup({
    maxClusterRadius: 50,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
});
```
<mcfile name="graph_redact.html" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\templates\graph_redact.html"></mcfile>

#### 6.1.2 事件处理优化
使用节流和防抖函数优化事件处理，减少事件触发频率，提升性能。

```javascript
// 节流函数
function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
```
<mcfile name="graph_redact.html" path="e:\逐梦航大的我\课程：大三\航空情报数据模型及数据库技术\INFODB\templates\graph_redact.html"></mcfile>

#### 6.1.3 坐标对齐优化
在缩放事件中添加防抖处理，确保坐标正确对齐。

```javascript
// 添加缩放事件监听，优化坐标对齐
map.on('zoomend', debounce(function(e) {
    // 重新渲染图层以确保坐标对齐
    if (waypointLayer) {
        waypointLayer.refreshClusters();
    }
    if (navaidLayer) {
        navaidLayer.refreshClusters();
    }
}, 100));
```

### 6.2 后端性能优化

#### 6.2.1 数据库查询优化
使用参数化查询和索引优化数据库查询性能。

#### 6.2.2 缓存机制
对频繁访问的数据实施缓存策略，减少数据库查询次数。

#### 6.2.3 错误处理
完善的错误处理机制，确保系统稳定性。

## 7. 系统部署与配置

### 7.1 环境要求

- Python 3.7+
- Flask 2.0+
- SQLite 2.0+
- 浏览器支持：Chrome, Firefox, Safari, Edge

### 7.2 安装与部署

1. **克隆项目**
   ```bash
   git clone <项目地址>
   cd INFODB
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv infodbVenv
   ```

3. **激活虚拟环境**
   - Windows: `infodbVenv\Scripts\activate`
   - Linux/Mac: `source infodbVenv/bin/activate`

4. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

5. **初始化数据库**
   系统会自动创建默认数据库和管理员账户。

6. **启动服务**
   ```bash
   python main.py
   ```

7. **访问系统**
   打开浏览器访问 `http://localhost:5000`

### 7.3 默认账户

- **用户名**: admin
- **密码**: admin123
- **权限**: 管理员

## 8. 系统安全

### 8.1 安全措施

- **用户认证**: 基于Flask的会话管理
- **权限控制**: 基于角色的访问控制
- **SQL注入防护**: 使用参数化查询
- **XSS防护**: 输入验证和输出编码
- **CSRF防护**: 使用Flask的CSRF保护

### 8.2 安全建议

- 定期更新系统密码
- 限制管理员账户的使用
- 定期备份数据库
- 避免在生产环境中使用开发模式
- 配置适当的防火墙规则

## 9. 未来发展规划

### 9.1 功能扩展

- **三维地图支持**: 集成Cesium.js实现三维地图可视化
- **数据导入/导出**: 支持多种格式的数据导入导出
- **用户自定义图层**: 允许用户创建和管理自定义图层
- **高级分析工具**: 提供航路分析、流量分析等高级功能
- **移动应用**: 开发移动客户端，支持离线访问

### 9.2 技术升级

- **数据库升级**: 考虑使用PostgreSQL等更强大的数据库系统
- **前端框架升级**: 迁移到React或Vue等现代前端框架
- **API优化**: 实现RESTful API规范，支持更多客户端
- **性能优化**: 进一步提升系统性能和响应速度
- **容器化部署**: 使用Docker实现容器化部署

## 10. 总结

数字化航图平台是一个功能完善、界面友好的航空情报数据管理与可视化系统，通过结合Flask后端和Leaflet.js前端，实现了高效的数据管理和直观的地图可视化功能。系统支持航空情报数据的全面管理，包括航路点、导航台、航段和航路的增删改查，同时提供了强大的航路编辑功能，允许用户在地图上直观地创建和修改航路。

系统采用模块化设计，代码结构清晰，易于维护和扩展。通过实施标记聚类、事件处理优化等技术，提升了系统性能和用户体验。完善的API接口设计，为系统与其他应用的集成提供了便利。

未来，系统可以通过扩展三维地图支持、增强数据分析能力、开发移动应用等方式，进一步提升其功能和价值，为航空领域的数据分析和决策提供更强大的支持。