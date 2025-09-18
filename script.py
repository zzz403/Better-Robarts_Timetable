def check_all_rooms_availability_sqlite_from_json(json_path, db_name="uoft_study_rooms.db", filter_item_ids=None):
    """从本地API JSON批量导入所有房间的可用时间，避免重复抓取，按itemId过滤"""
    if not os.path.exists(json_path):
        print(f"can not find: {json_path}")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'slots' not in data:
        print("JSON data structure is invalid, missing 'slots' field")
        return
    # 读取房间元数据
    csv_file = get_latest_csv_file()
    room_meta = {}
    if csv_file:
        with open(csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                room_meta[int(row['space_id'])] = row
    # 读取已存在的房间，避免重复
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT space_id FROM rooms')
    existing_rooms = set(row[0] for row in cursor.fetchall())
    # 按itemId分组slots
    slots_by_item = {}
    for slot in data['slots']:
        item_id = slot['itemId']
        if filter_item_ids and item_id not in filter_item_ids:
            continue
        slots_by_item.setdefault(item_id, []).append(slot)
    total_rooms = len(slots_by_item)
    print(f"JSON includes {total_rooms} rooms with time slots")
    imported = 0
    for item_id, slots in slots_by_item.items():
        # 插入房间元数据（如有）
        if item_id not in existing_rooms:
            meta = room_meta.get(item_id)
            if meta:
                cursor.execute('''
                    INSERT OR REPLACE INTO rooms (space_id, room_name, capacity_found_at, gid, url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    int(meta['space_id']),
                    meta['room_name'],
                    int(meta['capacity_found_at']),
                    int(meta['gid']),
                    meta['url']
                ))
                conn.commit()
        # 处理时间槽
        available_slots = []
        unavailable_slots = []
        for slot in slots:
            slot_info = {
                'start': slot['start'],
                'end': slot['end'],
                'item_id': slot['itemId'],
                'checksum': slot.get('checksum', ''),
            }
            if 'className' not in slot or slot['className'] != 's-lc-eq-checkout':
                slot_info['status'] = 'available'
                available_slots.append(slot_info)
            else:
                slot_info['status'] = 'unavailable'
                unavailable_slots.append(slot_info)
        # 删除旧数据
        query_date = slot['start'][:10] if slots else datetime.now().strftime('%Y-%m-%d')
        cursor.execute('DELETE FROM time_slots WHERE space_id = ? AND query_date = ?', (item_id, query_date))
        # 插入新数据
        for slot in available_slots + unavailable_slots:
            cursor.execute('''
                INSERT INTO time_slots (space_id, gid, start_time, end_time, status, item_id, checksum, query_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                int(room_meta.get(item_id, {}).get('gid', 0)),
                slot['start'],
                slot['end'],
                slot['status'],
                slot['item_id'],
                slot['checksum'],
                slot['start'][:10]
            ))
        conn.commit()
        imported += 1
        print(f"Installed room {item_id} with {len(available_slots) + len(unavailable_slots)} time slots")
    conn.close()
    print(f"Batch import completed, processed {imported} rooms")
import requests
import json
import csv
import sqlite3
from datetime import datetime, timedelta
import time
import os

def fetch_room_availability_api_raw(space_id, gid, start_date=None, end_date=None):
    """通过API获取指定房间的原始JSON数据"""
    
    # 如果没有指定日期，默认查询今天和明天
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"正在获取房间 {space_id} (gid:{gid}) 从 {start_date} 到 {end_date} 的原始数据...")
    
    # API端点
    api_url = "https://libcal.library.utoronto.ca/spaces/availability/grid"
    
    # 构建payload，使用传入的gid
    payload = {
        'lid': '3446',      # Library ID
        'gid': str(gid),    # 使用从CSV读取的gid
        'eid': str(space_id),  # Equipment/Space ID
        'seat': '0',
        'seatId': '0', 
        'zone': '0',
        'start': start_date,
        'end': end_date,
        'pageIndex': '0',
        'pageSize': '18'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://libcal.library.utoronto.ca/space/{space_id}',
        'Origin': 'https://libcal.library.utoronto.ca'
    }
    
    try:
        # 发送POST请求
        response = requests.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        
        # 解析JSON响应
        data = response.json()
        return data
        
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"Other error: {e}")
        return None

def process_slots_to_availability(slots):
    """将slots数组处理成可用/不可用时间槽格式，使用className判断"""
    available_slots = []
    unavailable_slots = []
    
    for slot in slots:
        slot_info = {
            'start': slot['start'],
            'end': slot['end'],
            'item_id': slot['itemId'],
            'checksum': slot.get('checksum', '')
        }
        
        # 根据className判断是否可用
        # 没有className或className不是's-lc-eq-checkout'的时间槽是可用的
        if 'className' not in slot or slot['className'] != 's-lc-eq-checkout':
            slot_info['status'] = 'available'
            available_slots.append(slot_info)
        else:
            slot_info['status'] = 'unavailable'
            unavailable_slots.append(slot_info)
    
    return {
        'available': available_slots,
        'unavailable': unavailable_slots,
        'total_slots': len(available_slots) + len(unavailable_slots)
    }

def fetch_room_availability_api(space_id, gid, start_date=None, end_date=None):
    """通过API获取指定房间的可用时间"""
    
    # 如果没有指定日期，默认查询今天和明天
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"getting availability for room {space_id} (gid:{gid}) from {start_date} to {end_date}...")
    # API端点
    api_url = "https://libcal.library.utoronto.ca/spaces/availability/grid"
    
    # 构建payload，使用传入的gid
    payload = {
        'lid': '3446',      # Library ID
        'gid': str(gid),    # 使用从CSV读取的gid
        'eid': str(space_id),  # Equipment/Space ID
        'seat': '0',
        'seatId': '0', 
        'zone': '0',
        'start': start_date,
        'end': end_date,
        'pageIndex': '0',
        'pageSize': '18'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://libcal.library.utoronto.ca/space/{space_id}',
        'Origin': 'https://libcal.library.utoronto.ca'
    }
    
    try:
        # 发送POST请求
        response = requests.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        
        # 解析JSON响应
        data = response.json()
        
        # 提取时间槽信息
        available_slots = []
        unavailable_slots = []
        
        if 'slots' in data:
            for slot in data['slots']:
                slot_info = {
                    'start': slot['start'],
                    'end': slot['end'],
                    'item_id': slot['itemId'],
                    'checksum': slot['checksum']
                }
                
                # 根据className判断是否可用
                # 没有className或className不是's-lc-eq-checkout'的时间槽是可用的
                if 'className' not in slot or slot['className'] != 's-lc-eq-checkout':
                    slot_info['status'] = 'available'
                    available_slots.append(slot_info)
                else:
                    slot_info['status'] = 'unavailable'
                    unavailable_slots.append(slot_info)

        print(f"found {len(available_slots)} available time slots, {len(unavailable_slots)} unavailable time slots")

        return {
            'available': available_slots,
            'unavailable': unavailable_slots,
            'total_slots': len(available_slots) + len(unavailable_slots)
        }
        
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"Other error: {e}")
        return None

def init_sqlite_database(db_name="uoft_study_rooms.db"):
    """初始化SQLite数据库"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # 创建房间表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            space_id INTEGER PRIMARY KEY,
            room_name TEXT,
            capacity_found_at INTEGER,
            gid INTEGER,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建时间槽表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            space_id INTEGER,
            gid INTEGER,
            start_time TEXT,
            end_time TEXT,
            status TEXT,
            item_id INTEGER,
            checksum TEXT,
            query_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (space_id) REFERENCES rooms (space_id)
        )
    ''')
    
    # 创建索引以提高查询性能
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_space_id ON time_slots (space_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_start_time ON time_slots (start_time)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_status ON time_slots (status)
    ''')
    
    conn.commit()
    conn.close()
    print(f"SQLite {db_name} init completed")

def save_rooms_to_sqlite(csv_filename, db_name="uoft_study_rooms.db"):
    """将房间信息从CSV导入到SQLite数据库"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        with open(csv_filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # 清空现有房间数据
            cursor.execute('DELETE FROM rooms')
            
            for row in reader:
                cursor.execute('''
                    INSERT OR REPLACE INTO rooms 
                    (space_id, room_name, capacity_found_at, gid, url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    int(row['space_id']),
                    row['room_name'],
                    int(row['capacity_found_at']),
                    int(row['gid']),
                    row['url']
                ))
            
            conn.commit()
            
            # 获取导入的房间数量
            cursor.execute('SELECT COUNT(*) FROM rooms')
            count = cursor.fetchone()[0]
            print(f"successfully imported {count} rooms into the database")
            
    except FileNotFoundError:
        print(f"can not find CSV file: {csv_filename}")
    except Exception as e:
        print(f"error occurred while importing room data: {e}")
    finally:
        conn.close()

def save_availability_to_sqlite(space_id, gid, availability_data, query_date, db_name="uoft_study_rooms.db"):
    """将可用时间保存到SQLite数据库"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # 删除该房间该日期的旧数据
        cursor.execute('''
            DELETE FROM time_slots 
            WHERE space_id = ? AND query_date = ?
        ''', (space_id, query_date))
        
        # 插入新数据
        for slot in availability_data['available'] + availability_data['unavailable']:
            cursor.execute('''
                INSERT INTO time_slots 
                (space_id, gid, start_time, end_time, status, item_id, checksum, query_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                space_id,
                gid,
                slot['start'],
                slot['end'],
                slot['status'],
                slot['item_id'],
                slot['checksum'],
                query_date
            ))
        
        conn.commit()
        print(f"房间 {space_id} 的 {len(availability_data['available']) + len(availability_data['unavailable'])} 个时间槽已保存到数据库")
        
    except Exception as e:
        print(f"保存时间槽数据时发生错误: {e}")
    finally:
        conn.close()

def get_available_rooms_from_sqlite(db_name="uoft_study_rooms.db"):
    """从SQLite数据库中读取所有房间"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT space_id, gid, room_name FROM rooms ORDER BY space_id')
        rooms = cursor.fetchall()
        print(f"从数据库中读取到 {len(rooms)} 个房间")
        return rooms
    except Exception as e:
        print(f"读取房间数据时发生错误: {e}")
        return []
    finally:
        conn.close()

def check_database_stats(db_name="uoft_study_rooms.db"):
    """检查数据库中的数据统计"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        print("📊 数据库统计信息:")
        print("=" * 50)
        
        # 检查房间表
        cursor.execute('SELECT COUNT(*) FROM rooms')
        room_count = cursor.fetchone()[0]
        print(f"房间总数: {room_count}")
        
        # 检查时间槽表
        cursor.execute('SELECT COUNT(*) FROM time_slots')
        slot_count = cursor.fetchone()[0]
        print(f"时间槽总数: {slot_count}")
        
        # 检查可用时间槽
        cursor.execute('SELECT COUNT(*) FROM time_slots WHERE status = "available"')
        available_count = cursor.fetchone()[0]
        print(f"可用时间槽: {available_count}")
        
        # 检查不可用时间槽
        cursor.execute('SELECT COUNT(*) FROM time_slots WHERE status = "unavailable"')
        unavailable_count = cursor.fetchone()[0]
        print(f"不可用时间槽: {unavailable_count}")
        
        # 按日期统计
        cursor.execute('SELECT query_date, COUNT(*) FROM time_slots GROUP BY query_date ORDER BY query_date')
        date_stats = cursor.fetchall()
        print(f"\n按日期统计:")
        for date, count in date_stats:
            print(f"  {date}: {count} 个时间槽")
        
        # 按房间统计 (前10个)
        cursor.execute('''
            SELECT r.space_id, r.room_name, COUNT(ts.id) as slot_count
            FROM rooms r
            LEFT JOIN time_slots ts ON r.space_id = ts.space_id
            GROUP BY r.space_id, r.room_name
            ORDER BY slot_count DESC
            LIMIT 10
        ''')
        room_stats = cursor.fetchall()
        print(f"\n房间时间槽统计 (前10个):")
        for space_id, room_name, count in room_stats:
            print(f"  {space_id} - {room_name}: {count} 个时间槽")
        
        # 按gid统计
        cursor.execute('''
            SELECT gid, COUNT(DISTINCT space_id) as room_count, COUNT(*) as slot_count
            FROM time_slots
            GROUP BY gid
            ORDER BY gid
        ''')
        gid_stats = cursor.fetchall()
        print(f"\n按gid统计:")
        for gid, room_count, slot_count in gid_stats:
            print(f"  gid {gid}: {room_count} 个房间, {slot_count} 个时间槽")
        
        # 检查最新数据的时间范围
        cursor.execute('SELECT MIN(start_time), MAX(end_time) FROM time_slots')
        time_range = cursor.fetchone()
        if time_range[0] and time_range[1]:
            print(f"\n时间范围: {time_range[0]} 到 {time_range[1]}")
        
        return {
            'room_count': room_count,
            'slot_count': slot_count,
            'available_count': available_count,
            'unavailable_count': unavailable_count
        }
        
    except Exception as e:
        print(f"查询数据库统计时发生错误: {e}")
        return None
    finally:
        conn.close()

def query_room_availability(space_id=None, db_name="uoft_study_rooms.db"):
    """查询特定房间的可用时间"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        if space_id:
            cursor.execute('''
                SELECT ts.start_time, ts.end_time, ts.status, r.room_name
                FROM time_slots ts
                JOIN rooms r ON ts.space_id = r.space_id
                WHERE ts.space_id = ? AND ts.status = "available"
                ORDER BY ts.start_time
            ''', (space_id,))
            results = cursor.fetchall()
            
            if results:
                print(f"\n房间 {space_id} 的可用时间:")
                print("-" * 50)
                for start_time, end_time, status, room_name in results:
                    print(f"  {start_time} - {end_time}")
                print(f"\n总计: {len(results)} 个可用时间槽")
            else:
                print(f"房间 {space_id} 没有可用时间或不存在")
        else:
            # 显示所有有可用时间的房间
            cursor.execute('''
                SELECT r.space_id, r.room_name, COUNT(*) as available_slots
                FROM time_slots ts
                JOIN rooms r ON ts.space_id = r.space_id
                WHERE ts.status = "available"
                GROUP BY r.space_id, r.room_name
                ORDER BY available_slots DESC
            ''')
            results = cursor.fetchall()
            
            print(f"\n所有房间的可用时间槽统计:")
            print("-" * 60)
            for space_id, room_name, count in results:
                print(f"  {space_id} - {room_name}: {count} 个可用时间槽")
            
    except Exception as e:
        print(f"查询房间可用时间时发生错误: {e}")
    finally:
        conn.close()

def save_availability_to_csv(space_id, availability_data, filename=None):
    """将可用时间保存到CSV文件"""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"room_{space_id}_availability_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['space_id', 'start_time', 'end_time', 'status', 'item_id', 'checksum']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        # 写入可用时间槽
        for slot in availability_data['available']:
            writer.writerow({
                'space_id': space_id,
                'start_time': slot['start'],
                'end_time': slot['end'],
                'status': slot['status'],
                'item_id': slot['item_id'],
                'checksum': slot['checksum']
            })
        
        # 写入不可用时间槽
        for slot in availability_data['unavailable']:
            writer.writerow({
                'space_id': space_id,
                'start_time': slot['start'],
                'end_time': slot['end'],
                'status': slot['status'],
                'item_id': slot['item_id'],
                'checksum': slot['checksum']
            })
    
    print(f"可用时间数据已保存到 {filename}")
    return filename

def get_available_rooms_from_csv(csv_filename="uoft_study_rooms_20250916_145956.csv"):
    """从之前生成的房间CSV文件中读取所有房间ID"""
    rooms = []
    try:
        with open(csv_filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rooms.append(row['space_id'])
        print(f"从 {csv_filename} 中读取到 {len(rooms)} 个房间")
        return rooms
    except FileNotFoundError:
        print(f"找不到文件 {csv_filename}")
        return []

def check_all_rooms_availability_sqlite(start_date=None, end_date=None, db_name="uoft_study_rooms.db"):
    """检查所有房间的可用时间并存储到SQLite数据库 - 优化版本，避免重复抓取"""
    
    # 设置查询日期
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # 清空所有time_slots表数据，保证全新插入
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM time_slots')
        conn.commit()
        conn.close()
        print('All previous time_slots data cleared.')
    except Exception as e:
        print(f'Error clearing time_slots: {e}')

    query_date = start_date

    # 从数据库获取房间列表
    rooms = get_available_rooms_from_sqlite(db_name)

    if not rooms:
        print("没有找到房间列表，请先导入房间数据")
        return
    
    # 读取CSV房间元数据，用于补全额外抓取的房间信息
    csv_file = get_latest_csv_file()
    room_meta = {}
    if csv_file:
        with open(csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                room_meta[int(row['space_id'])] = row
    
    # 记录已处理的房间，避免重复
    processed_rooms = set()
    success_count = 0
    error_count = 0
    bonus_rooms_count = 0  # 额外获得的房间数量
    
    for i, (space_id, gid, room_name) in enumerate(rooms):
        if space_id in processed_rooms:
            print(f"跳过房间 {space_id} - {room_name} (已在之前的API调用中处理)")
            continue
            
        print(f"\n处理房间 {i+1}/{len(rooms)}: {space_id} - {room_name} (gid:{gid})")
        
        try:
            # 调用API获取数据
            response_data = fetch_room_availability_api_raw(space_id, gid, start_date, end_date)
            
            if response_data and 'slots' in response_data:
                # 按itemId分组所有返回的slots
                slots_by_item = {}
                for slot in response_data['slots']:
                    item_id = slot['itemId']
                    slots_by_item.setdefault(item_id, []).append(slot)
                
                # 处理目标房间的数据
                if space_id in slots_by_item:
                    target_slots = slots_by_item[space_id]
                    availability = process_slots_to_availability(target_slots)
                    save_availability_to_sqlite(space_id, gid, availability, query_date, db_name)
                    processed_rooms.add(space_id)
                    success_count += 1
                    print(f"  目标房间 {space_id}: {len(availability['available'])} 可用 + {len(availability['unavailable'])} 不可用")
                
                # 处理额外获取的房间数据
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                
                for item_id, slots in slots_by_item.items():
                    if item_id != space_id and item_id not in processed_rooms:
                        # 检查该房间是否已在数据库中
                        cursor.execute('SELECT space_id FROM rooms WHERE space_id = ?', (item_id,))
                        if not cursor.fetchone():
                            # 从CSV获取元数据并插入
                            meta = room_meta.get(item_id)
                            if meta:
                                cursor.execute('''
                                    INSERT OR REPLACE INTO rooms (space_id, room_name, capacity_found_at, gid, url)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (
                                    int(meta['space_id']),
                                    meta['room_name'],
                                    int(meta['capacity_found_at']),
                                    int(meta['gid']),
                                    meta['url']
                                ))
                                conn.commit()
                        
                        # 处理时间槽数据
                        availability = process_slots_to_availability(slots)
                        bonus_gid = int(room_meta.get(item_id, {}).get('gid', 0))
                        save_availability_to_sqlite(item_id, bonus_gid, availability, query_date, db_name)
                        processed_rooms.add(item_id)
                        bonus_rooms_count += 1
                        
                        bonus_name = room_meta.get(item_id, {}).get('room_name', f'未知房间{item_id}')
                        print(f"  额外获得房间 {item_id} - {bonus_name}: {len(availability['available'])} 可用 + {len(availability['unavailable'])} 不可用")
                
                conn.close()
                
                # 添加延迟避免请求过于频繁
                time.sleep(0.5)
            else:
                print(f"  获取房间 {space_id} 数据失败")
                error_count += 1
                
        except Exception as e:
            print(f"  处理房间 {space_id} 时发生错误: {e}")
            error_count += 1
    
    print(f"\n批量处理完成:")
    print(f"  目标成功: {success_count} 个房间")
    print(f"  额外获得: {bonus_rooms_count} 个房间")
    print(f"  失败: {error_count} 个房间")
    print(f"  总计处理: {len(processed_rooms)} 个房间")
    print(f"  原计划: {len(rooms)} 个房间")

def get_latest_csv_file():
    """获取最新的房间CSV文件"""
    csv_files = [f for f in os.listdir('.') if f.startswith('uoft_study_rooms') and f.endswith('.csv')]
    if not csv_files:
        return None
    # 按文件名排序，最新的在最后
    csv_files.sort()
    return csv_files[-1]

def main():
    print("UofT Study Room Availability Query System")
    print("=" * 50)
    
    db_name = "uoft_study_rooms.db"
    
    # Initialize database
    print("1. Initializing SQLite database...")
    init_sqlite_database(db_name)
    
    # Find the latest CSV file
    csv_file = get_latest_csv_file()
    if csv_file:
        print(f"2. Found CSV file: {csv_file}")
        print("   Importing room data into the database...")
        save_rooms_to_sqlite(csv_file, db_name)
    else:
        print("2. No room CSV file found. Please run test.py first to generate the room list.")
        return
    
    # Ask for user action
    print("\nPlease choose an action:")
    print("1. Test a single room")
    print("2. Batch fetch availability for all rooms within two weeks (API)")
    print("3. Exit")

    choice = input("Enter your choice (1/2/3): ").strip()

    if choice == "1":
        # Test a single room
        space_id = input("Enter room ID (default 30514): ").strip() or "30514"
        gid = input("Enter gid (default 7314): ").strip() or "7314"
        
        print(f"\nTesting room {space_id} (gid: {gid})...")
        availability = fetch_room_availability_api(space_id, gid)
        
        if availability:
            print(f"\nAvailability summary for room {space_id}:")
            print(f"  Total timeslots: {availability['total_slots']}")
            print(f"  Available timeslots: {len(availability['available'])}")
            print(f"  Unavailable timeslots: {len(availability['unavailable'])}")
            
            print(f"\nAvailable timeslot details:")
            for slot in availability['available'][:10]:  # show first 10 only
                print(f"  {slot['start']} - {slot['end']}")
            
            if len(availability['available']) > 10:
                print(f"  ... and {len(availability['available']) - 10} more available timeslots")
            
            # Save to database
            query_date = datetime.now().strftime('%Y-%m-%d')
            save_availability_to_sqlite(space_id, gid, availability, query_date, db_name)
            
        else:
            print(f"Failed to fetch availability for room {space_id}.")
    
    elif choice == "2":
        # Batch process all rooms (API method, original logic)
        print("\nStarting batch fetch of availability for all rooms (API)...")
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d')
        print(f"Query date range: {start_date} to {end_date}")
        print("This may take a while. Please be patient...")
        check_all_rooms_availability_sqlite(start_date, end_date, db_name)
    elif choice == "3":
        print("Exiting program.")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
