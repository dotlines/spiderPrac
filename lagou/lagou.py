# -*- coding: utf-8 -*-
"""
 @desc:
 @author: adam
 @software: PyCharm on 18-8-12
"""
import requests
from requests.adapters import HTTPAdapter
from lxml import etree
import io
import json
from fake_useragent import UserAgent
import pymongo
from time import sleep
import random
from time import time

class Lagou(object):
    # 构建通用请求头
    ua = UserAgent()
    headers = {
        'User-Agent': ua.random,
        'Referer': '',  # url without '.json'
        #如果被反爬，cookie可能需要更新
        'Cookie': 'JSESSIONID=ABAAABAAAFCAAEGBBB4142F20938248BB2478F3E58144AC; Hm_lvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1533828435; _ga=GA1.2.270700076.1533828435; user_trace_token=20180809232715-b1c8888a-9be8-11e8-b9f2-525400f775ce; LGUID=20180809232715-b1c88c33-9be8-11e8-b9f2-525400f775ce; X_HTTP_TOKEN=3086fbe35a0d1fd40e7578a16f535b8b; showExpriedIndex=1; showExpriedCompanyHome=1; showExpriedMyPublish=1; hasDeliver=0; index_location_city=%E5%B9%BF%E5%B7%9E; _gid=GA1.2.105723379.1533990288; TG-TRACK-CODE=hpage_code; _gat=1; LGSID=20180814012036-310b3c09-9f1d-11e8-a37b-5254005c3644; PRE_UTM=; PRE_HOST=; PRE_SITE=https%3A%2F%2Fwww.lagou.com%2Fgongsi%2FallCity.html%3Foption%3D163-0-0; PRE_LAND=https%3A%2F%2Fwww.lagou.com%2F; login=false; unick=""; _putrc=""; Hm_lpvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1534180860; LGRID=20180814012059-3f3e3384-9f1d-11e8-a37b-5254005c3644',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Connection': 'keep-alive',
        'Content-Length': '',
        'Host': 'www.lagou.com',
        'Origin': 'https://www.lagou.com'
    }

    # 连接数据库
    _myclient = pymongo.MongoClient('localhost', 27017)
    _mydb = _myclient['lagoudb']
    _url_col = _mydb['status_url']
    _company_col = _mydb['company_list']
    _city_col = _mydb['cities']

    _retry_times = 5       #用于重试的次数
    #按城市进行抓取
    def __init__(self,city):
        self.city = city        #未校验城市名


    def request_url(self,method,url,headers,**args):
        try:
            response = method(url,headers=headers,**args)
            # = response.content.decode('utf-8','ignore')  # html
            return response   # 返回响应
        except requests.exceptions.ConnectionError as e:
            print(e)
            Lagou._url_col.insert({'bad_url':url})  #记录错误的链接
            # self.request_url(method,url,headers) #retry暂未解决

    #判断url是否重复
    def is_repeat_url(self,url):
        if Lagou._url_col.find({'success_url': url}).count() != 0:
            return True

    #获取并存储拉勾上所有的城市列表
    def download_city(self):
        url = 'https://www.lagou.com/gongsi/allCity.html?option=215-0-0'
        #去重判断
        if self.is_repeat_url(url):
            return '已获取所有城市列表'
        #请求城市列表
        city_headers = Lagou.headers
        city_res = self.request_url(requests.get,url,city_headers)
        city_html = etree.HTML(city_res.content.decode('utf8','ignore'))
        city_lists = city_html.xpath('//table[@class="word_list"]/tr/td/ul/li/a')
        Lagou._url_col.insert({'success_url': url}) #添加已抓取的链接
        #数据入库
        for city in city_lists:
            Lagou._city_col.insert({'city_name':city.xpath('string(.)'),'city_url':city.xpath('string(./@href)')})

        return 'cities saved!'

    #获取指定城市的所有公司
    def get_company_list(self):
        #查找城市url
        city_col = Lagou._mydb.cities
        city_url = city_col.find_one({'city_name':self.city})['city_url']
        status_code = 1 #状态码用于表示抓取状态，默认1代表本次成功抓取该城市
        #去重判断
        if self.is_repeat_url(city_url+'.json'):
            print('%s 公司已抓取过'%self.city)
            status_code = 2  #状态码为2，表示该城市已经抓取
            return status_code
        #请求城市的公司列表
        cl_headers = Lagou.headers
        cl_headers['Referer'] = city_url
        cl_headers['User-Agent'] = Lagou.ua.random
        # cl_headers2 = {
        #     'User-Agent': self.ua.random,
        #     'Referer': city_url,  # url without '.json'
        #     'Cookie': 'JSESSIONID=ABAAABAAAFCAAEGBBB4142F20938248BB2478F3E58144AC; Hm_lvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1533828435; _ga=GA1.2.270700076.1533828435; user_trace_token=20180809232715-b1c8888a-9be8-11e8-b9f2-525400f775ce; LGUID=20180809232715-b1c88c33-9be8-11e8-b9f2-525400f775ce; X_HTTP_TOKEN=3086fbe35a0d1fd40e7578a16f535b8b; _putrc=6F2F4FED79124B7A; login=true; unick=%E6%8B%89%E5%8B%BE%E7%94%A8%E6%88%B73070; showExpriedIndex=1; showExpriedCompanyHome=1; showExpriedMyPublish=1; hasDeliver=0; index_location_city=%E5%B9%BF%E5%B7%9E; TG-TRACK-CODE=index_search; _gid=GA1.2.105723379.1533990288; _gat=1; LGSID=20180811202447-89784d70-9d61-11e8-ba8e-525400f775ce; PRE_UTM=; PRE_HOST=; PRE_SITE=; PRE_LAND=https%3A%2F%2Fwww.lagou.com%2Fgongsi%2F2-0-0; gate_login_token=a11927046bd1035997e3d742392a2df46399e358fdcdf349; LGRID=20180811202449-8a37bc8c-9d61-11e8-ba8e-525400f775ce; Hm_lpvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1533990289',
        #     'Accept': 'application/json, text/javascript, */*; q=0.01',
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        #     'Connection': 'keep-alive',
        #     'Content-Length': '39',
        #     'Host': 'www.lagou.com',
        #     'Origin': 'https://www.lagou.com',
        # }
        pn = 1
        while True:
            pyload = {
                'pn': pn,  # 第0页和第1页是一样的
                'first': False,
                'havemark': 0,
                'sortField': 0
            }
            company = {}
            company['uid'] = city_url + '.json?pageNo=%s' % str(pn)  # 添加一个id用于去重
            # 判断城市翻页是否重复
            if Lagou._company_col.find({'uid': company['uid']}).count() != 0:
                print('此页面已抓取')
                pn += 1
                continue

            company_res = self.request_url(requests.post,city_url+'.json',cl_headers,data=pyload)
            try:
                company_data = json.loads(company_res.text)
            except (TypeError,ValueError) as err:   #爬虫被识别可能无法返回json内容，需要retry
                print('Error:',err)
                print('爬虫被识别，稍等片刻...')
                sleep(random.uniform(0,30))       #随机休息30秒内的时间
                print('第%d次重试'%(Lagou._retry_times-self._retry_times+1))
                self._retry_times -= 1
                if self._retry_times <= 0:
                    print('%s无法成功抓取'%self.city)
                    status_code = 0#状态码为0，表示抓取有误
                    self._retry_times = Lagou._retry_times  # 重置实例的retry次数
                    return status_code
                return self.get_company_list()
            company = {**company,**company_data}

            try:
                if not company['result']: #终止条件
                    break
            except KeyError as e:   #判断是否被识别为爬虫
                print(e)
                continue
            Lagou._company_col.insert(company)#指定城市的公司存入数据库
            print('完成%s第%d页公司列表获取'%(self.city,pn))
            pn += 1
            sleep(random.random())  # 防止访问过快
        Lagou._url_col.insert({'success_url': city_url+'.json'}) #记录完成抓取的城市
        Lagou._city_col.update({'city_name':self.city},{'$set':{'city_status':1}})#讲抓取过的城市标记状态为1
        print('完成 %s 抓取'%self.city)
        status_code = 1
        return status_code#状态码默认值


    #执行获取所有城市的所有公司
    def all_city_company(self):
        self.download_city()    #抓取所有城市的链接，若已抓取，则跳过
        ccol = Lagou._city_col.find()
        count = 1
        for city in ccol:
            start_time = time()
            self.city = city['city_name']
            # self.city = '深圳'
            print('开始抓取%s的公司'%self.city)
            if self.get_company_list() == 1:  #状态码为1，正常执行
                end_time = time()
                print('完成第%d个城市的抓取，还剩%d个城市;耗时%d秒' % (count, ccol.count() - count, end_time - start_time))
                print('------------------------------------------')
                sleep(random.uniform(0, 30))  # 每抓完一个城市休息0~30秒
                count += 1
                # continue  #若以下语句有本次循环的其他语句则continue
            elif self.get_company_list() == 2:  #判断已经抓取则进入下一个城市
                print('已完成第%d个城市的抓取，还剩%d个城市' % (count, ccol.count() - count))
                print('------------------------------------------')
                count += 1
                # continue  #若以下语句有本次循环的其他语句则continue
            else:
                print('%s有误，无法完成抓取，尝试下一个城市'%self.city)
                # continue  #若以下语句有本次循环的其他语句则continue
        print('完成所有城市的获取！！')



    def company_profile(self,company):
        pass

    def get_position_list(self,company):
        pass

    def posititon_detail(self,position):
        pass

    #更新数据使用update 示例
    # col = mydb['company_list']
    # url = 'https://www.lagou.com/gongsi/215-0-0.json?pageNo='
    # for i in col.find():
    #     col.update({'_id': i['_id']}, {'$set': {'uid': url + str(i['pageNo'])}})


if __name__ == '__main__':
    lg = Lagou('重庆')
    # lg.get_company_list()
    lg.all_city_company()








