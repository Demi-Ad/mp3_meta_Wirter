import os
import taglib
import time
from selenium import webdriver
from dateutil.parser import parse
from datetime import datetime
from bs4 import BeautifulSoup
import re
import threading
import queue






my_queue = queue.Queue()  # 쓰레드 결과


# 쓰레드 결과를 담기위한 데코레이터
def storeInQueue(f):
    def wrapper(*args):
        my_queue.put(f(*args))
    return wrapper


# 메타데이터 삭제
def song_meta_remover(files):

    meta_tags = ['ALBUM', 'ARTIST', 'COMMENT', 'DATE',
                 'DISCNUMBER', 'GENRE', 'TITLE', 'TRACKNUMBER'] # 태그 8종

    for file in files:
        song = taglib.File(file)
        for tag in meta_tags:
            try:
                del song.tags[tag]
            except:
                pass
            finally:
                song.save()


# mp3 파일의 경로 , Disc 폴더를 모두 가져옴
def file_serach(root_dir):
    mp3_dir = [] # 폴더 리스트
    mp3_path = [] # mp3파일들의 경로 리스트
    for (path, dir, files) in os.walk(root_dir): # 목표 폴더를 모두 순회
        for file in files:
            if os.path.splitext(file)[1].lower() == '.mp3': # 확장자가 mp3일경우
                mp3_path.append(os.path.join(path, file)) # mp3 리스트 추가
        mp3_dir.append(dir) # 폴더리스트 추가
    mp3_dir = sum(mp3_dir, []) # 2차원 리스트를 1차원리스트로 변환
    mp3_dir = [x.upper() for x in mp3_dir] # 폴더명을 대문자화
    mp3_dir = list(filter(Disc_find, mp3_dir)) # DISC 폴더만 필터링
    return mp3_path, mp3_dir


@storeInQueue
def get_meta(url):

    print("셀레니움 로딩중....\n")

    # 셀레니움 기본설정
    driver_path = None # 수정하세요
    options = webdriver.ChromeOptions()
    options.add_experimental_option(
        "excludeSwitches", ["enable-logging"])
    options.add_argument('headless')  
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko")
    driver = webdriver.Chrome(driver_path, options=options)
    


    driver.get(url)  # 셀레니움으로 url 오픈
    time.sleep(1)  # 1초 대기

    print("셀레니움 로딩완료")

    req = driver.page_source  # 셀레니움으로 html 받아옴

    soup = BeautifulSoup(req, 'html.parser')  # 받아온 html을 bs4로 파싱

    meta_title = soup.select('#album_infobit_large > tbody')[0]  # 테이블 셀렉트

    info = []  # 임시로 사용할 리스트

    for a in meta_title.find_all("tr"): #tr 태그마다 반복
        info.append(a.get_text().split('\n')) # tr태그에 텍스트를 받아옴

    info = sum(info, [])  # 2차원 리스트를 1차원으로 변환
    info = list(filter(None, info))  # 변환한 1차원 리스트에서 공백제거

    info_tag = info[0:len(info)-1:2]  # 인덱스 슬라이싱으로 딕셔너리의 키를 가져옴
    info_data = info[1:len(info)-1:2]  # 인덱스 슬라이싱으로 딕셔너리의 값을 가져옴
    info_temp = [info_tag, info_data]  # 딕셔너리로 만들기위한 임시 2차원 리스트

    info_meta = dict(zip(*info_temp))  # 딕셔너리

    meta_cred = meta_title.find_all(
        'tr', attrs={'class': 'maincred'})[0]  # <<< 부연설명

    data_cred = []  # 임시로 사용할 리스트

    for i in meta_cred:
        data_cred.append(i.get_text().split('/'))

    arti = data_cred[0][0]  # 첫번째 키의 값을 알기위해 변수화

    arits_key = dict(zip(data_cred[0], data_cred[1]))

    info_meta.update(arits_key)


    Album_meta = driver.find_element_by_xpath(
        '//*[@id="innermain"]/h1/span[1]').get_attribute('textContent')  # 엘범명
    Genre_meta = driver.find_element_by_xpath(
        '/html/body/div[4]/table/tbody/tr[1]/td[2]/div[2]/div/div[4]').get_attribute('textContent').split('\n')[-1]  # 장르

    commet_meta = info_meta.get('Catalog Number')  # 카탈로그
    Date_meta = parse(info_meta.get('Release Date')).strftime('%Y-%m-%d')  # 날짜
    Artist_meta = info_meta.get(arti)  # 아티스트


    driver.close()

    metas = {
        'ALBUM': Album_meta,
        'COMMENT': commet_meta,
        'DATE': Date_meta,
        'GENRE': Genre_meta,
        'ARTIST': Artist_meta
    }
    print('- - - GET METAS - - - ')
    for key, value in metas.items():
        print('{0} : {1}'.format(key, value))

    return metas

# DISC 폴더 필터링 함수
def Disc_find(dir):
    if re.search('DISC', dir) != None:
        return True


def insert_get_meta(files, meta_dic, mp3_dir):

    max_Disc = len(mp3_dir)  # 디스크 넘버에 숫자구함
    for mp3_file in files:

        temp = mp3_file.split('\\')[-1]  # 경로 구분자 '\'로 나눠서 맨마지막 파일명을 변수화
        mp3_title = re.split('[0-9][0-9]', temp)[-1]  # [0-9][0-9] 음악명 슬라이싱
        mp3_track = str(temp[0:2])  # 맨앞 숫자 2개를 strng 으로 변환
        mp3_Disc = mp3_file.split('\\')[-2]

        song = taglib.File(mp3_file)  # 음악태그 라이브러리 오픈
        for key, value in meta_dic.items(): # get_meta 함수로 가져온 5가지 태그를 적용
            song.tags[key] = value
            song.tags['TITLE'] = mp3_title.split('.mp3')[0] # 음악에 타이틀은 숫자를 제외한 파일명
            song.tags['TRACKNUMBER'] = mp3_track # 음악에 트랙넘버는 파일명에 앞 숫자
            if max_Disc != 0: # 디스크 폴더가 0개 이상이라면
                song.tags['DISCNUMBER'] = str( 
                    '{0}/{1}'.format(mp3_Disc[-1], max_Disc)) # 현재디스크폴더에 번호 / 디스크 폴더에 총갯수
            else:
                song.tags['DISCNUMBER'] = '1/1' # 디스크넘버가 없다면 1/1
        song.save()


def main(root_path, input_url):

    t1 = threading.Thread(target=get_meta, args=(input_url,)) 
    t1.start()

    files, mp3_dir = file_serach(root_path)  # 파일위치 리스트
    song_meta_remover(files)  # 메타리스트 삭제

    t1.join()
    meta_dic = my_queue.get()

    insert_get_meta(files, meta_dic, mp3_dir)


if __name__ == '__main__':

    root_path = input('파일경로 : ')
    input_url = input('URL : ')

    start_time = time.time()
    main(root_path, input_url)
    
    end_time = time.time()

    print('\n\n')
    print('작업완료 : {0}'.format(end_time - start_time))
