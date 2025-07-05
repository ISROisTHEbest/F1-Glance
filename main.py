from livef1.adapters.realtime_client import RealF1Client
from flask import Flask, jsonify
import threading
import asyncio
import fastf1
from datetime import datetime, timezone, timedelta
import os

cache_dir = 'cache'

if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

fastf1.Cache.enable_cache(cache_dir)

client = RealF1Client(topics=["TimingData", "LapCount", "TrackStatus", "SessionInfo", "SessionStatus"])

data = {}

app = Flask('F1 Glance API')

@client.callback("basic_handler")
async def handle_data(records):
    global session_end_time
    qno = ''
    for driver_no, key in [('44', 'HAM'), ('16', 'LEC')]:
        try:
            driver = next(d for d in records.get("TimingData", []) if d["DriverNo"] == driver_no)
            try:
                pos = driver['Position']
                if key not in data:
                    data[key] = {}
                data[key]['pos'] = pos
            except:
                pass
            try:
                gap = driver['GapToLeader']
            except:
                pass
            try:
                gap = driver['TimeDiffToFastest']
            except:
                pass
            try:
                for i in range(3):
                    try:
                        gapraw = driver[f'Stats_{i}_TimeDiffToFastest']
                        if gapraw != '':
                            gap = gapraw
                            qno = i
                    except:
                        pass
            except:
                pass
                
                
            if not str(gap).startswith('+') and not gap or not isinstance(gap, str):
                if int(pos) == 1:
                    gap = "LEADER"
                elif gap == '':
                    gap = '--'
                 
            if key not in data:
                data[key] = {}
            data[key]['gap'] = gap
            
        except:
            pass

    try:
        raw = records.get("TrackStatus", [{}])[0]
        msg = raw['Message']
        if msg == 'Yellow':
            data['track'] = 'y'
        elif msg == 'Red':
            data['track'] = 'r'
        elif msg == 'SCDeployed':
            data['track'] = 'sc'
        elif msg == 'VSCDeployed':
            data['track'] = 'vsc'
        else:
            data['track'] = ''
    except:
        pass
    
    try:
        raw = records.get("SessionInfo", [{}])[0]
        roundno = raw['Meeting_Number']
        sessiontype = raw['Name'].replace('Practice', 'FP').replace('Qualifying', 'Q').replace('Sprint Qualifying', 'SQ').replace(' ', '') + str(qno)
        data['session'] = [sessiontype, roundno]
        if sessiontype != 'Race':
            h, m, s = map(int, raw['GmtOffset'].split(':'))
            gmt_offset = timedelta(hours=h, minutes=m, seconds=s)
            
            start = datetime.fromisoformat(raw['StartDate']).replace(tzinfo=timezone.utc) - gmt_offset
            end = datetime.fromisoformat(raw['EndDate']).replace(tzinfo=timezone.utc) - gmt_offset
            
            data['timeinfo'] = [start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")]
    except:
        pass
    
    try:
        raw = records.get("LapCount", [{}])[0]
        current = raw['CurrentLap']
        total = raw['TotalLaps']
        
        data['timeinfo'] = [current, total]
    except:
        pass
    
    try:
        raw = records.get("SessionStatus", [{}])[0] 
        if raw['status'] == 'Not Started' or raw['status'] == 'Ends' or raw['status'] == 'Ended' or raw['status'] == 'Finalised':
            schedule = fastf1.get_event_schedule(2025)
            
            stime = None
            session_key = None

            for i in range(1, 6):
                col = f'Session{i}DateUtc'
                for j in schedule[col].to_dict():
                    session_time = schedule[col][j].to_pydatetime().replace(tzinfo=timezone.utc)
                    if session_time > datetime.now(timezone.utc):
                        if stime is None or session_time < stime:
                            stime = session_time
                            session_key = (j, col)

            if session_key:
                row_idx, col_name = session_key
                round_no = schedule.loc[row_idx]['RoundNumber']
                

                session_index = int(col_name.replace('Session', '').replace('DateUtc', ''))
                session_name = {1: 'FP1', 2: 'FP2', 3: 'FP3', 4: 'Q', 5: 'R'}.get(session_index, f'S{session_index}')
                
                data['session'] = [session_name, int(round_no)]
                data['status'] = stime.strftime('%Y-%m-%d %H:%M:%S')
        else:
            data['status'] = 's'
                        
    except:
        pass

@app.route('/getdata')
def get_data():
    return jsonify(data)

def run_flask():
    app.run(host='0.0.0.0', port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Run LiveF1 client
asyncio.run(client.run())
