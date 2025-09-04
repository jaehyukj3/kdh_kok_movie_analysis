import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import pandas as pd
import os

# 파이썬 스크립트의 기본 인코딩을 UTF-8로 설정
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 크롤링할 영화 리스트 (영화 제목과 리뷰 타입 리스트)
movies = {
    'KPop Demon Hunters': ['top_critics', 'user'],
    'The King of Kings': ['top_critics', 'user']
}
base_url = 'https://www.rottentomatoes.com/m/{}/reviews?type={}'

# 데이터를 저장할 폴더 생성
os.makedirs('movie_data', exist_ok=True)

# 크롬 드라이버 설정
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

for title, review_types in movies.items():
    print(f"'{title}' 리뷰 데이터 수집 시작...")
    all_reviews_list = []
    
    slug = title.lower().replace(' ', '_')

    # 영화 크롤링 시작 전 5초 대기
    time.sleep(5)

    for review_type in review_types:
        url = base_url.format(slug, review_type)
        author_type = 'Top Critic' if review_type == 'top_critics' else 'Audience'
        
        print(f"  - {author_type} 리뷰 크롤링 중... {url}")

        try:
            driver.get(url)
            time.sleep(3) # 페이지 로딩 대기

            # '더 보기' 버튼 클릭 횟수 제한
            max_clicks = 15 # 최대 15번만 클릭
            click_count = 0

            while click_count < max_clicks:
                try:
                    load_more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'rt-button[data-qa="load-more-btn"]'))
                    )
                    load_more_button.click()
                    time.sleep(2)
                    click_count += 1
                    print(f" > '더 보기' 버튼 클릭... (현재 횟수: {click_count}/{max_clicks})")
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                    # 버튼을 찾지 못하거나 클릭할 수 없으면 (모든 리뷰 로드 완료)
                    print(" > 모든 리뷰를 로드했거나 더 이상 버튼을 찾을 수 없습니다.")
                    break
            
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            if review_type == 'top_critics':
                review_rows = soup.find_all('div', class_='review-row')
            elif review_type == 'user':
                review_rows = soup.find_all('div', class_='audience-review-row')
            else:
                review_rows = []

            if not review_rows:
                print(f"🚨 '{title}'에 대한 {author_type} 리뷰를 찾을 수 없습니다.")
            else:
                for review in review_rows:
                    score = None # 점수 변수 초기화

                    if review_type == 'top_critics':
                        critic_name_element = review.find('a', class_='display-name')
                        review_text_element = review.find('p', class_='review-text')
                        review_date_element = review.find('span', {'data-qa': 'review-date'})
                        
                        # 비평가 점수: 'sentiment' 속성을 사용하여 'POSITIVE'/'NEGATIVE' 가져오기
                        score_icon_element = review.find('score-icon-critics')
                        if score_icon_element and 'sentiment' in score_icon_element.attrs:
                            sentiment = score_icon_element['sentiment']
                            if sentiment == 'POSITIVE':
                                score = 'Fresh'
                            elif sentiment == 'NEGATIVE':
                                score = 'Rotten'

                    elif review_type == 'user':
                        critic_name_element = review.find('span', class_='audience-reviews__name')
                        review_text_element = review.find('p', class_='audience-reviews__review')
                        review_date_element = review.find('span', class_='audience-reviews__duration')

                        # 사용자 점수: 'score' 속성을 사용하여 별점 값 가져오기
                        score_group_element = review.find('rating-stars-group')
                        if score_group_element and 'score' in score_group_element.attrs:
                            score_value = score_group_element['score']
                            score = f"{score_value}/5.0"
                            
                    critic_name = critic_name_element.text.strip() if critic_name_element else None
                    review_text = review_text_element.text.strip() if review_text_element else None
                    review_date = review_date_element.text.strip() if review_date_element else None
                    
                    all_reviews_list.append({
                        'author_type': author_type,
                        'critic_name': critic_name,
                        'review_date': review_date,
                        'review_text': review_text,
                        'score': score # 딕셔너리에 점수 추가
                    })

        except Exception as e:
            print(f"🚨 '{title}' {author_type} 데이터 처리 중 알 수 없는 오류가 발생했습니다: {e}")

    if all_reviews_list:
        df_reviews = pd.DataFrame(all_reviews_list)
        df_reviews.to_csv(f'movie_data/{title}_all_reviews.csv', index=False, encoding='utf-8')
        print(f"✅ '{title}'의 모든 리뷰 파일이 성공적으로 저장되었습니다.")
    else:
        print(f"⚠️ '{title}'의 모든 리뷰를 찾을 수 없어 파일을 생성하지 않았습니다.")

driver.quit()