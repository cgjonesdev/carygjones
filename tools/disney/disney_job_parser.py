import os
from scraper import *

if not os.path.isfile('disney_job_links.txt'):
    driver.get('https://jobs.disneycareers.com/search-jobs/Disney%20Media%20%26%20Entertainment%20Distribution%2C%20python/California?orgIds=391-28648&kt=1&acm=21579%2C26715&alp=6252001-5332921&alt=3')

    jobs = []
    job_links = lambda: [elem.get_property('href') for elem in driver.find_elements(By.TAG_NAME, 'a') if '/job/' in elem.get_property('href')]
    max_pages = int(driver.find_element(By.CLASS_NAME, 'pagination-current').get_attribute('max'))
    current_page_num_elem = lambda: driver.find_element(By.CLASS_NAME, 'pagination-current')
    current_page_num = lambda: int(current_page_num_elem().get_attribute('value'))
    remote_plus_icon = lambda: driver.find_element(By.ID, 'custom_fields.flextype-toggle')
    remote_yes_checkbox = lambda: driver.find_element(By.ID, 'custom_fields.flextype-filter-1')
    next_button = lambda: driver.find_element(By.CLASS_NAME, 'next')
    while current_page_num() < max_pages:
        wait('next_button().click()')
        #wait('remote_plus_icon().click()')
        #wait('remote_yes_checkbox().click()')
        wait("job_link()")
        jobs += [job for job in job_links() if 'software-engineer' in job]
        print(job_links())

    pretty_links = '\n'.join(sorted(list(set(jobs))))
    with open('disney_job_links.txt', 'w') as _:
        _.write(pretty_links)

else:
    with open('disney_job_links.txt') as _:
        jobs = _.read().split('\n')

    filtered_jobs = []

    for job in jobs:
        #os.system(f'open {job}')
        try:
            driver.get(job)
            soup = bs(driver.page_source, 'html.parser')
            python_match = re.search('.*(python).*', soup.text, re.I)
            cali_match = re.search('.*(california).*', soup.text, re.I)
            java_match = re.search('.*( java ).*', soup.text, re.I)
            datalake_match = re.search('.*( data.lake ).*', soup.text, re.I)
            animation_match = re.search('.*( animation ).*', soup.text, re.I)
            manager_match = re.search('.*( manager ).*', soup.text, re.I)
            remote_match = re.search('.*(remote).*', soup.text, re.I)
            if not python_match or not cali_match or datalake_match or not remote_match or java_match or animation_match or manager_match:
                continue
            filtered_jobs += [f'Title: {soup.find(id="job-title-scrape").text}, Job link: {job}']
            print(filtered_jobs[-1])
        except:
            pass
    print(f'{len(filtered_jobs)}: jobs')
    with open('disney_filtered_job_links.txt', 'w') as _:
        _.write('\n'.join(filtered_jobs))

driver.quit()
