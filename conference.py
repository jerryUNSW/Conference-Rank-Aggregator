
# coding: utf-8

# In[39]:


#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
import requests
import urllib.request
import time
import threading


# In[47]:


import time, threading
class MyThread(threading.Thread):
    
    def __init__(self,func,args=()):
        super(MyThread,self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  
        except Exception:
            return None


# In[40]:


def fetch_ggs():
    # find the url to the summarised GGS ratings 
    url_GGS = "http://gii-grin-scie-rating.scie.es/ratingSearch.jsf"
    response = requests.get(url_GGS)
    soup = BeautifulSoup(response.text, "html.parser")
    for i in soup.find("div",{"class":"entry"}).findAll("td"):
        txt=i.text.strip()
        if re.match("^Download", txt):
            file_url="http://gii-grin-scie-rating.scie.es"+i.find("a")["href"]
    r = requests.get(file_url)
    with open('GGS.xlsx', 'wb') as f:
        f.write(r.content)
    GGS = pd.read_excel('GGS.xlsx', index_col=0, header = 1)
    return GGS[GGS.columns[:6]].copy()

def fetch_csrankings():
    url_csRankings = 'http://csrankings.org/#/index?all'
    response = requests.get(url_csRankings)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("div",{"class":"table-responsive"}).find("table")
    theads = []
    tbodies = []
    for tag in table.contents:
        if tag.name == "tbody":
            tbodies.append(tag)
        if tag.name == "thead":
            theads.append(tag)
    result = []
    for i in range(len(tbodies)):
        Area = theads[i+1].text.replace("[off | on]","").strip() 
        tbody = tbodies[i]
        for tr in tbody.contents:
            if tr.name == "tr":
                td1=tr.find("td")
                Subarea = td1.contents[2].replace("\n","").strip()
                for a in td1.find('div').find('table').find('table').findAll('a'):
                    result.append([a.text,Subarea,Area])
    csRankings=pd.DataFrame(result,columns=["Conference Abbreviation", "Subarea", "Area"])
    csRankings["Listed_IN_CSRankings"]="YES"
    return csRankings

def fetch_arwu():
    url_arwu = 'http://www.shanghairanking.com/subject-survey/conferences.html'
    response = requests.get(url_arwu)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table",{"id":"UniversityRanking"})
    result = []
    for tr in table.contents:
        if tr.name == "tr":
            tmp = []
            for entry in tr.contents:
                txt = entry.string.replace("\n","").strip()
                if txt != "":
                    tmp.append(txt)
            result.append(tmp)
    arwu = pd.DataFrame(result[1:],columns = result[0])
    del arwu["Academic Subject"]
    arwu["Listed_In_ARWU"]="YES"
    return arwu


# In[41]:


def fetch_core():
    # core_root="http://portal.core.edu.au/conf-ranks/?search=&by=all&source=CORE2018&sort=arank&page="
    core_root="http://portal.core.edu.au/conf-ranks/?search=&by=all&source=all&sort=arank&page="
    response = requests.get(core_root+"1")
    soup = BeautifulSoup(response.text, "html.parser")
    maxPageNumber=-1
    for i in soup.find("div",{"id":"search"}).findAll("a"):
        if re.match("[0-9]+",i.text.strip()):
            if maxPageNumber<int(i.text.strip()):
                maxPageNumber=int(i.text.strip())
    result = []
    for pagenumber in range(0,maxPageNumber):
        url = core_root + str(pagenumber+1);
        # sorted by rank,getting A and A* from the first few pages
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        trs = soup.findAll('tr') #  table rows
        data = []
        data.append(trs[0].findAll('b'))
        for i in range(0,len(trs)):
            data.append(trs[i].findAll('td'))  
        for i in range(0,len(data)):
            for j in range(0,len(data[i])):
                data[i][j]=data[i][j].text
        Data = pd.DataFrame(data[1:],columns=data[0]).dropna()
        for col in Data.columns:
            Data[col] = Data[col].map(lambda s:s.replace("\n","").strip())
        if ('A' in Data["Rank"].unique()) | ('A*' in Data["Rank"].unique()):
            result.append(Data)
        else :
            break
    core = result[0]
    for i in range(1,len(result)):
        core=core.append(result[i])
    core = core[(core["Rank"] == "A*") ].append(core[(core["Rank"] == "A") ])
    core.reset_index(drop=True,inplace=True)
    core["Listed_In_CORE"]="YES"
    core["index_"] = core.index
    core["Acronym"]=core.apply(
        lambda row: "NA-"+str(row['index_']) if row['Acronym']=="" else row['Acronym'],
        axis=1
    )
    del core["index_"]
    return core


# In[42]:


def fetch_ccf():
    root = 'https://www.ccf.org.cn'
    response = requests.get("https://www.ccf.org.cn/xspj/gyml/")
    soup = BeautifulSoup(response.text, "html.parser")
    area_href=[]
    for i in soup.find("div",{"class":"snv"}).findAll("a"):
        area_href.append(i["href"])
    names = ["Computer architecture/parallel and distributed computing/storage systems",
            "Computer Networks","Web & information security","Software Engineering/System Software/Programming Language",
             "Database/data mining/content retrieval","Computer science theory","Computer Graphics and Multimedia",
             "AI","Human-Computer Interaction and Pervasive Computing","Multidisciplinary/comprehensive,emgering"]
    df_list=[]
    for i,ref in enumerate(area_href[1:-1]):
        area=names[i]
        url=root+ref
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        mid=soup.find("div",{"class":"m-text-mg"})
        for num in [3,4]:
            ul=mid.findAll("ul")[num]
            lll=[]
            for item in ul.findAll("li"):
                lll.append([ i.text for i in item.findAll("div")])
            tmp=pd.DataFrame(lll[1:])
            if num==3:
                tmp["ccf_rating"]="A"
            if num==4:
                tmp["ccf_rating"]="B"
            tmp.columns=["num","Acronym","Title","Publisher","url","ccf_rating"]
            tmp["area"]=area
            del tmp["num"]
            df_list.append(tmp)
    ccf_conference = pd.concat(df_list).reset_index(drop=True)
    ccf_conference["from CCF"]="YES"
    ccf_conference.columns=['Acronym','Title','Publisher','website','CCF_Rank','CCF_Area','Listed_IN_CCF']
    return ccf_conference


# In[58]:


t1=MyThread(fetch_ggs)
t2=MyThread(fetch_csrankings)
t3=MyThread(fetch_arwu)
t4=MyThread(fetch_core)
t5=MyThread(fetch_ccf)
t1.start()
t2.start()
t3.start()
t4.start()
t5.start()
t1.join()
t2.join()
t3.join()
t4.join()
t5.join()
GGS_important=t1.get_result()
csRankings = t2.get_result()
arwu=t3.get_result()
core=t4.get_result()
ccf_conference=t5.get_result()


# In[15]:


arwu.to_excel("arwu.xlsx",index=False)
csRankings.to_excel("csRankings.xlsx",index=False)
core.to_excel("core.xlsx",index=False)
ccf_conference.to_excel("ccf.xlsx",index=False)


# In[16]:


GGS_important.columns=['Title_ggs', 'Acronym', 'GGS_Class', 'GGS_Rating', 'GGS_Qualified_Classes','GGS_Collected_Classes']
csRankings.columns=["Acronym",'Subarea_CSRankings', 'Area_CSRankings','Listed_IN_CSRankings']
arwu.columns=["Title_arwu","Acronym","Percentage Voted","Listed_In_ARWU"]
core.columns = ["Title_core","Acronym",'Source', 'core_Rank', 'hasData?', 'Primary FoR','comments', 'avg_rating_core','Listed_IN_CORE']


# In[17]:


def clean_acronym(x):
    if re.match("^.*/.*$",x):
        return x.split("/")[0]
    if x=="NIPS":
        return "NeurIPS"
    if x=="CaiSE":
        return "CAiSE"
    if x=="EuroCrypt":
        return "EUROCRYPT"
    else:
        return x


# In[18]:


all_=None
for data_ in [ccf_conference,arwu, csRankings, core, GGS_important]:
    data_["Acronym"].fillna("",inplace=True)
    data_["Acronym"] = data_["Acronym"].map(clean_acronym)
    if all_ is None:
        all_=data_
    else:
        all_=pd.merge(all_, data_, on='Acronym', how='outer')
all_["Title"].fillna(all_['Title_ggs'],inplace=True)
all_["Title"].fillna(all_['Title_core'],inplace=True)
all_["Title"].fillna(all_['Title_arwu'],inplace=True)
del all_["Title_ggs"]
del all_['Title_core']
del all_['Title_arwu']
all_= all_.fillna('')


# In[19]:


all_[(all_.Listed_IN_CORE=="YES")|(all_.Listed_In_ARWU=="YES")|      (all_.Listed_IN_CCF=="YES")|(all_.Listed_IN_CSRankings=="YES")].to_excel("important_conferences.xlsx",index=False)
# all_.to_excel("all.xlsx",index=False)

