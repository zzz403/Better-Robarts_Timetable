#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询特定房间在特定日期的时间槽数据
"""

import sqlite3
from datetime import datetime

def query_room_data(room_identifier, target_date):
    """查询房间在指定日期的数据"""
    
    db_name = 'uoft_study_rooms.db'
    
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # 查找房间 - 支持按ID或名称搜索
        if room_identifier.isdigit():
            cursor.execute('SELECT space_id, room_name, gid FROM rooms WHERE space_id = ?', (int(room_identifier),))
        else:
            cursor.execute('SELECT space_id, room_name, gid FROM rooms WHERE room_name LIKE ?', (f'%{room_identifier}%',))
        
        rooms = cursor.fetchall()
        
        print('🔍 房间搜索结果:')
        print('=' * 50)
        if not rooms:
            print('❌ 没有找到匹配的房间')
            return
        
        for room in rooms:
            print(f'📍 ID: {room[0]}, Name: {room[1]}, GID: {room[2]}')
        
        # 使用第一个匹配的房间
        space_id = rooms[0][0]
        room_name = rooms[0][1]
        
        print(f'\n📅 查询房间 {space_id} ({room_name}) 在 {target_date} 的时间槽:')
        print('=' * 60)
        
        # 查询指定日期的时间槽
        cursor.execute('''
            SELECT start_time, end_time, status, query_date 
            FROM time_slots 
            WHERE space_id = ? AND query_date = ?
            ORDER BY start_time
        ''', (space_id, target_date))
        
        slots = cursor.fetchall()
        
        if slots:
            available_count = 0
            unavailable_count = 0
            
            print('⏰ 时间槽详情:')
            for slot in slots:
                status_symbol = '🟢' if slot[2] == 'available' else '🔴'
                status_text = '可用' if slot[2] == 'available' else '不可用'
                print(f'{status_symbol} {slot[0]} - {slot[1]} ({status_text})')
                
                if slot[2] == 'available':
                    available_count += 1
                else:
                    unavailable_count += 1
            
            print(f'\n📊 统计结果:')
            print(f'   ✅ 可用: {available_count} 个时间槽')
            print(f'   ❌ 不可用: {unavailable_count} 个时间槽')
            print(f'   📈 总计: {len(slots)} 个时间槽')
            
        else:
            print(f'❌ 没有找到 {target_date} 的数据')
            
            # 查看该房间所有可用的日期
            cursor.execute('SELECT DISTINCT query_date FROM time_slots WHERE space_id = ? ORDER BY query_date', (space_id,))
            available_dates = cursor.fetchall()
            
            if available_dates:
                print(f'\n📆 该房间可用的日期:')
                for date in available_dates:
                    print(f'   📅 {date[0]}')
            else:
                print('   ⚠️  数据库中没有该房间的任何时间槽数据')
        
    except sqlite3.Error as e:
        print(f'❌ 数据库错误: {e}')
    except Exception as e:
        print(f'❌ 发生错误: {e}')
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # 查询房间2253在2025-09-27的数据
    query_room_data('2253', '2025-09-27')
    
    print('\n' + '='*60)
    
    # 也可以按名称搜索
    query_room_data('GSR 2D', '2025-09-27')