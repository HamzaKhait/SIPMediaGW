#!/usr/bin/env python

import sys
import time
import os
import requests
import json
from browsing import Browsing
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

jitsiFQDN = os.environ.get('WEBRTC_DOMAIN')
if not jitsiFQDN:
    jitsiFQDN = "rendez-vous.renater.fr"

confMapperURL = os.environ.get('CONFMAPPER')
if not confMapperURL:
    confMapperURL = ""#"https://rendez-vous.renater.fr/conf-api/conferenceMapper"

UIHelperPath = os.environ.get('UI_HELPER_PATH')

UIKeyMap = { "#": "window.JitsiMeetUIHelper.executeCommand('show-dtmf-menu')",
             "0": "window.JitsiMeetUIHelper.executeCommand('toggle-tts')",
             "1": "window.JitsiMeetUIHelper.executeCommand('toggle-audio')",
             "2": "window.JitsiMeetUIHelper.executeCommand('toggle-video')",
             "3": "window.JitsiMeetUIHelper.executeCommand('toggle-chat')",
             "4": "window.JitsiMeetUIHelper.executeCommand('toggle-tile-view')",
             "5": "window.JitsiMeetUIHelper.executeCommand('toggle-raise-hand')",}

if not UIHelperPath:
    UIHelperPath = "file:///var/UIHelper/index.html"
    UIHelperConfig =  json.load(open('/var/UIHelper/config_sample.json'))
    UIHelperConfig['domain'] = 'https://{}'.format(jitsiFQDN)

    if confMapperURL:
        UIHelperConfig['ivr']['confmapper_url'] = confMapperURL.rsplit('/',1)[0]+'/'
        UIHelperConfig['ivr']['confmapper_endpoint'] = confMapperURL.rsplit('/',1)[1]

    with open('/var/UIHelper/config.json', 'w', encoding='utf-8') as f:
        json.dump(UIHelperConfig, f, ensure_ascii=False, indent=4)

class Jitsi (Browsing):

    def getRoomName(self):
        reqUrl = '{}?id={}'.format(confMapperURL,self.room)
        print("ConfMapper request URL: "+reqUrl, flush=True)
        r = requests.get(reqUrl, verify=False)
        mapping = json.loads(r.content.decode('utf-8'))
        if 'conference' in mapping:
            return mapping['conference']
        elif 'error' in mapping:
            raise Exception(mapping['error'])
        else:
            return

    def setUrl(self):
        if UIHelperPath:
            self.url = '{}?room_id={}&display_name={}'.format(UIHelperPath, self.room, self.name)
            self.chromeOptions.add_argument('--disable-web-security')
            self.UIKeyMap = UIKeyMap
        else:
            urlBase = ''
            if confMapperURL:
                try:
                    urlConference = self.getRoomName().split('@')
                    urlDomain = urlConference[1].split('conference.')[1]
                    urlBase = 'https://{}/{}'.format(urlDomain, urlConference[0])
                except Exception as exc:
                    print("Failed to get room URL:", exc, flush=True)
                    return
            else:
                urlBase =  'https://{}/{}'.format(jitsiFQDN, self.room)

            self.url += urlBase
            self.url += '#userInfo.displayName="' + self.name + '"'
            self.url += '&config.enableNoisyMicDetection=false'
            self.url += '&config.prejoinPageEnabled=false'

        print("Web browsing URL: "+self.url, flush=True)

    def browse(self, driver):

        # Swith to iframe
        try:
            WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR,"#jitsiConferenceFrame0")))
            jitsiUrl = self.driver.execute_script("return window.JitsiMeetUIHelper.room.jitsiApiClient._url;")
            print("Jitsi URL: "+jitsiUrl, flush=True)
        except Exception as e:
            print("Iframe not found", flush=True)
            jitsiUrl = self.driver.execute_script("return window.location.href;")
            print("Jitsi URL: "+jitsiUrl, flush=True)

        # Validate MOTD
        try:
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"#motd_do_not_show_again")))
            element.click()
        except Exception as e:
            print("MOTD not found", flush=True)

        # Accept Cookies
        try:
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"#cookie_footer > section > section > section > a")))
            element.click()
        except Exception as e:
            print("Cookies banner not found", flush=True)

        #Swith back from iframe
        try:
            driver.switch_to.default_content()
        except Exception as e:
            print("Swith back from iframe error", flush=True)

    def unset(self):
        try:
            self.driver.execute_script("window.JitsiMeetUIHelper.room.jitsiApiClient.dispose()")
            WebDriverWait(self.driver, 5).until_not(EC.presence_of_element_located((By.CSS_SELECTOR,"#jitsiConferenceFrame0")))
        except Exception as e:
            print("Iframe error", flush=True)
