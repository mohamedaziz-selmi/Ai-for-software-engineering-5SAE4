"""Generate reproducible synthetic datasets for the Cerebro report."""
from pathlib import Path
import csv, random
ROOT = Path(__file__).parent
R = random.Random(42)
CATEGORIES = ["Web Development","Mobile Development","Design","Writing","Marketing","Data & AI","Video & Audio","Business"]
SKILLS = {"Web Development":["React","Java","Spring","TypeScript"],"Mobile Development":["Flutter","iOS","Android"],"Design":["Figma","branding","UX"],"Writing":["copywriting","blogging","editing"],"Marketing":["SEO","social media","ads"],"Data & AI":["Python","pandas","machine learning"],"Video & Audio":["Premiere","podcast","audio editing"],"Business":["Excel","finance","consulting"]}
def write(name, fields, rows):
    with (ROOT/name).open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def listings():
    rows=[]
    for i in range(1500):
        c=R.choice(CATEGORIES); skills=R.sample(SKILLS[c], k=min(2,len(SKILLS[c]))); title=f"{R.choice(['Professional','Reliable','Custom','Fast'])} {c} service"; desc=f"I help clients with {c.lower()} using {', '.join(skills)}. Clear scope, practical communication, and reviewable delivery are included."; rows.append({'id':i,'title':title,'description':desc,'category':c,'skills':'|'.join(skills)})
    write('listings.csv', rows[0].keys(), rows)
def demand():
    rows=[]
    for i in range(1500):
        row={'id':i,'category':R.choice(CATEGORIES),'price':round(R.uniform(30,2500),2),'description_length':R.randint(60,1200),'rating':round(R.uniform(2.5,5),2),'response_time_hours':round(R.uniform(1,72),2),'delivery_days':R.randint(1,45),'skill_demand_index':round(R.uniform(.1,1),3)}
        row['high_order_volume']=int(row['skill_demand_index']*.5+row['rating']/5*.25+min(row['description_length']/1200,1)*.15+int(row['response_time_hours']<24)*.1 >= .55); rows.append(row)
    write('demand.csv', rows[0].keys(), rows)
def transactions():
    rows=[]
    for i in range(20000):
        amount=round(R.lognormvariate(4.4,1),2); velocity=R.randint(1,12); row={'id':i,'amount':amount,'velocity_24h':velocity,'account_age_days':R.randint(1,1800),'distance_km':round(R.uniform(0,12000),1),'chargeback_history':int(R.random()<.03),'fraud':0}
        row['fraud']=int((amount>1800 and velocity>7) or (row['account_age_days']<10 and row['chargeback_history']) or R.random()<.010); rows.append(row)
    write('transactions.csv', rows[0].keys(), rows)
def profiles():
    rows=[]
    for i in range(500):
        duplicate=i in {101,202,303}; rows.append({'id':i,'name':f'User {i if not duplicate else i-1}','email':f'user{i}@example.com' if i%37 else f'user{i}@mailinator.com','skills':'Python|React','years_experience':R.randint(0,12),'duplicate_of':i-1 if duplicate else '','skills_contradict':int(i%43==0),'overlapping_jobs':int(i%47==0),'burst_count':R.randint(1,8) if i%29==0 else R.randint(1,3),'ground_truth':int(duplicate or i%37==0 or i%43==0 or i%47==0)})
    write('profiles.csv', rows[0].keys(), rows)
def skill_demand():
    rows=[{'skill':s,'demand_index':round(R.uniform(.25,1),3)} for values in SKILLS.values() for s in values]; write('skill_demand.csv', rows[0].keys(), rows)
if __name__=='__main__':
    listings(); demand(); transactions(); profiles(); skill_demand(); print('Generated synthetic Cerebro datasets with seed 42.')
