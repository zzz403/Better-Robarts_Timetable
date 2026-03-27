import sqlite3

db_name = 'uoft_study_rooms.db'
room_id = 35838

try:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    print(f"🔍 查询房间 {room_id}...\n")
    
    # 查找房间信息
    cursor.execute('SELECT space_id, room_name, gid, capacity_found_at, url FROM rooms WHERE space_id = ?', (room_id,))
    room = cursor.fetchone()
    
    if room:
        print(f"✅ 找到房间 {room_id}:")
        print(f"  ID: {room[0]}")
        print(f"  名称: {room[1]}")
        print(f"  GID: {room[2]}")
        print(f"  容量: {room[3]}")
        print(f"  URL: {room[4]}")
        
        # 查询时间槽统计
        cursor.execute('SELECT COUNT(*), MIN(query_date), MAX(query_date) FROM time_slots WHERE space_id = ?', (room_id,))
        stats = cursor.fetchone()
        print(f"\n时间槽统计:")
        print(f"  总数: {stats[0]}")
        if stats[0] > 0:
            print(f"  日期范围: {stats[1]} 到 {stats[2]}")
    else:
        print(f"❌ 数据库中没有找到房间 {room_id}")
        
        # 显示数据库统计
        cursor.execute('SELECT MIN(space_id), MAX(space_id), COUNT(*) FROM rooms')
        range_info = cursor.fetchone()
        print(f"\n当前数据库中的房间:")
        print(f"  ID范围: {range_info[0]} - {range_info[1]}")
        print(f"  总房间数: {range_info[2]}")
        
        # 显示几个示例房间
        cursor.execute('SELECT space_id, room_name FROM rooms ORDER BY space_id LIMIT 5')
        print(f"\n前5个房间:")
        for r in cursor.fetchall():
            print(f"  {r[0]}: {r[1]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 查询出错: {e}")
