import os
import subprocess
import pickle
import pytesseract
import string
import nltk
from geotext import GeoText
import re
from datetime import date
import json


def extract_all_entities(document_name):
    input_file_ocred = './upload/' + document_name
    input_file_raw = './upload/' + document_name
    print(document_name)
    subprocess.call([r'pdftotext', '-l', '0', input_file_ocred,
                     './trailapp/temp/' + document_name[:-4] + '.txt'])
    # sudo apt-get install -y poppler-utils
    with open(r'./trailapp/temp/' + document_name[:-4] + '.txt', encoding='cp1252') as infile:
        contents = infile.read()
    with open(r'./trailapp/sintu_files/data.pkl','rb') as fd:
        data_ocr = pickle.load(fd)
    contents_tess = data_ocr[document_name.split('_')[1]]
    with open(r'./trailapp/data_top_half.pkl','rb') as fd:
        data_ocr_top_half = pickle.load(fd)

    contents_tess_top_half = data_ocr_top_half[document_name.split('_')[1]]
    data_tess = pytesseract.image_to_data(r'./trailapp/sintu_files/docs/' + document_name.split('_')[1]+'.jpg', output_type='dict')
    words = set(nltk.corpus.words.words('en'))
    words = set([w.upper() for w in words])
    names = nltk.corpus.names.words()
    names =set([n.upper() for n in names])

    # subtract names form words
    words = words - names

    def detect_name_candidates(text):
        candidates_list = []
        matches = re.findall(r"([A-Z][A-z]+,?\s?[A-Z]?[.]?\s?[A-Z][A-z]+)",
                             text.replace('Patient','patient'))
        for match in matches:
            if len(match.split()) > 1:
                candidates_list.append(match)

        return candidates_list

    def filter_names(names_list):
        names_list_filtered = []
        black_list_words = ['PHARMACY','TAB','REFILL','PERMANENTE','AVE','EAST']
        for name in names_list:
            name_2 = name.replace(',','')
            if any(n.upper() in names for n in name_2.split()) and (len(GeoText(name_2.title()).cities) < 1) \
                    and (not all(n.upper() in words for n in name_2.split())) and (not any(n.upper() in black_list_words
                                                                                           for n in name_2.split())):
                names_list_filtered.append(name)

        return names_list_filtered

    name_candidates = detect_name_candidates(contents_tess_top_half)
    name_candidates = filter_names(name_candidates)
    name_entity_value = ''
    if name_candidates:
        name_entity_value = name_candidates[0]

    # # Rx# Entity
    x = 0
    if any(t in contents for t in ["Rx","RX","rx"]):
        Rx_index, RX_index, rx_index = len(contents),len(contents),len(contents)
        if 'Rx' in contents:
            Rx_index = contents.index("Rx")
        if 'RX' in contents:
            RX_index = contents.index("RX")
        if 'rx' in contents:
            rx_index = contents.index("rx")
        x = min(Rx_index,RX_index,rx_index)
    elif "Prescription Number" in contents:
        pivot = "Prescription Number"
        x = contents.index(pivot)
    else:
        x = 0

    ok = contents[x:]
    temp = ""
    start = 0
    for m in ok:
        start = start + 1
        if m.isdigit() or (len(temp)>3 and (m==' ' or m=='-')):
            temp = temp + m
            if (temp not in ok) or len([c for c in temp if c.isdigit()])>12:
                break

    rx_entity_value = temp[:-1]

    # # Drug Name Entity

    def extract_drug_name(content):
        drug_name = set()
        pattern = re.compile(r"(?=.[A-Za-z]+).+(?=.TAB|.TABLET|.TABS|[\s]*MG|[\s]*mg)")
        for _string in content:
            if len(_string) != 0:
                try:
                    match = pattern.match(_string)
                    if match:
                        match_string = match.group(0).strip()
                        if match_string[-1].isnumeric():
                            match_string += ' MG'
                        else:
                            match_string += ' TABS'

                        match_string = match_string.replace("Strength: ", "").replace("strength: ", "")
                        drug_name.add(match_string)
                except ValueError:
                    print(_string)
        return drug_name

    content = contents.replace("Remove Watermark", "").replace("Wondershare PDFelement", '').split("\n")
    drug_name_entity_value = extract_drug_name(content)

    # # NDC Entity

    def check_forward(data, index):
        data = " ".join(data)
        chunks = data.split()
        # chunks_count = len(chunks)
        # data_count = len(data)
        # if chunks_count == data_count and chunks[index].isnumeric():
        #     print(data, index)
        #     return chunks[index]
        # for _content in data:
        #     pass
        return chunks[index] if (index<len(chunks) and chunks[index].isnumeric()) else None

    def extract_ndc(content):
        ndc_pattern = re.compile(r"(?<=NDC|ndc)(?:.*?)([\d-]+)")
        remove_punctuations = str.maketrans("", "", string.punctuation)
        for idx, _content in enumerate(content):
            match = ndc_pattern.findall(_content)
            if match:
                return match[0]
            else:
                _content = _content.translate(remove_punctuations).split()
                match_index = _content.index("NDC") if "NDC" in _content else -1
                if match_index > -1:
                    return check_forward(content[idx+1:idx+len(_content)+1], match_index)

    content = contents.replace("Remove Watermark", "").replace("Wondershare PDFelement", '').split("\n")
    ndc_entity_value = extract_ndc(content)

    # # Filled Date Entity

    def dist(p1,p2):
        return ((((p2[0] - p1[0]) ** 2) + ((p2[1] - p1[1]) ** 2)) ** 0.5)

    def get_nearest_index(data,ignore_indices):
        dindex = ignore_indices[0]
        x,y = data['left'][dindex] + (data['width'][dindex] / 2), data['top'][dindex] + (data['height'][dindex] / 2)
        min_dist = 100000
        nearest_index = 0
        for indd in range(len(data['top'])):

            if indd in ignore_indices:
                continue

            curr_dist = dist([x,y],
                [data['left'][indd] + (data['width'][indd] / 2), data['top'][indd] + (data['height'][indd] / 2)])

            if curr_dist<min_dist:
                min_dist = curr_dist
                nearest_index = indd

        return nearest_index

    def max_Date(dat):
        all_dates = []
        for d in dat:
            mx = d.split('/')
            year = int(mx[2])
            month = int(mx[0])
            day = int(mx[1])
            dates = date(year, month, day)
            all_dates.append(dates)

        if len(all_dates)<1:
            return ''

        year = max(all_dates).year
        month = max(all_dates).month
        day = max(all_dates).day

        return str(month)+'/'+str(day)+'/'+str(year)


    # In[19]:


    data = data_tess

    date_entity_value = ''

    found_flag = False

    for dindex,text in enumerate(data['text']):
        #print('main debug text',text)
        if any(t in text.lower() for t in ['date']):
            ignore_indices = [dindex]
            iter_index = 0
            max_iter = 100
            # initalize with next number box
            nearest_index = dindex + 1

            if nearest_index<len(data['text'])-1 and (bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index]))):
                date_entity_value = data['text'][nearest_index]
                found_flag = True
                break

            while nearest_index<len(data['text'])-1 and (not len(re.findall('[0-9]+[\s\/]+[0-9]+[c\/]+[0-9]+', data['text'][nearest_index]))>0):
                nearest_index = nearest_index + 1

            # if box is too far off then inti with closest box
            if dist([data['left'][dindex] + (data['width'][dindex] / 2),
                     data['top'][dindex] + (data['height'][dindex] / 2)],
                    [data['left'][nearest_index] + (data['width'][nearest_index] / 2),
                     data['top'][nearest_index] + (data['height'][nearest_index] / 2)]) > 200:
                nearest_index = get_nearest_index(data, ignore_indices)

                # print('debug', data['text'][nearest_index])
            while not (len(re.findall(r'[0-9]+[\s\/]+[0-9]+[\s\/]+[0-9]+', data['text'][nearest_index]))>0):
                iter_index += 1

                # printt('debug iter_index',iter_index,'text',text)
                if iter_index > max_iter:
                    break

                # printt('debug',data['text'][nearest_index])

                ignore_indices.append(nearest_index)
                nearest_index = get_nearest_index(data, ignore_indices)

                # printt('debug2',data['text'][nearest_index])
                #
                # print('debug3',all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                #     replace('$','').replace('*','').replace('%','').strip()))
                #
                # print('debug4',(bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index].replace('%','')))))

            if (len(re.findall(r'[0-9]+[\s\/]+[0-9]+[\s\/]+[0-9]+', data['text'][nearest_index]))>0):
                date_entity_value = data['text'][nearest_index]
                found_flag = True
                break

    if not found_flag: # date entity not found still
        #translate_table = dict((ord(char), None) for char in string.punctuation)
        pattern = '\d+/\d+/\d+'
        date_entity_value = max_Date(re.findall(pattern,contents_tess))

    # # Day Supply Entity
    data = data_tess
    supply_entity_value = ''
    for dindex,text in enumerate(data['text']):
        if any(t in text.lower() for t in ['supply']):
            ignore_indices = [dindex]
            iter_index = 0
            max_iter = 100
            nearest_index = get_nearest_index(data,ignore_indices)

            while (not (all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                    replace('$','').replace('*','').replace('%','').strip()) and
                        (bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index]))))):
                iter_index += 1

                if iter_index >max_iter:
                    break

                ignore_indices.append(nearest_index)
                nearest_index = get_nearest_index(data, ignore_indices)

            if all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                    replace('$','').replace('*','').replace('%','').strip()):
                try:
                    if float(data['text'][nearest_index].replace('$','').replace('*','').replace('%','').strip())<5000:
                        supply_entity_value = data['text'][nearest_index]
                        found_flag = True
                        break
                except:
                    pass

    # # Quantity
    def extract_quantity(content):
        insensitive_qty_match = re.compile(r"(?<=Qty)[\s:;]*(\d+)")
        remove_punctuations = str.maketrans("", "", string.punctuation)
        for idx, _content in enumerate(content):
            _content =  _content.replace("Quantity", "Qty").replace("QTY", "Qty")
            match = re.findall(r"(Qty)", _content)
            if match:
                match = insensitive_qty_match.findall(_content)
                if match:
                    return match[0]
                else:
                    _content = _content.translate(remove_punctuations).split()
                    match_index = _content.index("Qty")
                    if match_index > -1:
                        return check_forward(content[idx+1:idx+len(_content)+1], match_index)
                    else:
                        return "Not Found"

    # In[22]:
    content = contents.replace("Remove Watermark", "").replace("Wondershare PDFelement", '').split("\n")
    quantity_entity_value = extract_quantity(content)

    if quantity_entity_value == "Not Found" or (not quantity_entity_value):
        data = data_tess

        for dindex,text in enumerate(data['text']):
            if any(t in text.lower() for t in ['quantity','qty']):
                ignore_indices = [dindex]
                iter_index = 0
                max_iter = 100
                nearest_index = get_nearest_index(data,ignore_indices)
                while (not (all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                        replace('$','').replace('*','').replace('%','').strip()) and
                            (bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index]))))):
                    iter_index += 1

                    if iter_index >max_iter:
                        break

                    ignore_indices.append(nearest_index)
                    nearest_index = get_nearest_index(data, ignore_indices)

                if all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                        replace('$','').replace('*','').replace('%','').strip()):
                    try:
                        if float(data['text'][nearest_index].replace('$','').replace('*','').replace('%','').strip())<1000:
                            quantity_entity_value = data['text'][nearest_index]
                            found_flag = True
                            break
                    except:
                        pass

    if quantity_entity_value == "Not Found" or (not quantity_entity_value):
        quantity_entity_value = ''

    copay_entity_value =''
    found_flag = False

    #LOOP1
    for dindex,text in enumerate(data['text']):
        #print('main debug text',text)
        if any(t in text.lower() for t in ['co-pay','pay:','charges','due:','copay','received','amountoue:','youpay']):
            ignore_indices = [dindex]
            iter_index = 0
            max_iter = 100

            # initalize with next number box
            nearest_index = dindex + 1
            while not bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index].replace('%',''))):
                nearest_index = nearest_index+1

            # if box is too far off then inti with closest box
            if dist([data['left'][dindex] + (data['width'][dindex] / 2),
                     data['top'][dindex] + (data['height'][dindex] / 2)],
                    [data['left'][nearest_index] + (data['width'][nearest_index] / 2),
                     data['top'][nearest_index] + (data['height'][nearest_index] / 2)])>200:
                nearest_index = get_nearest_index(data, ignore_indices)

            while (not (all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                    replace('$','').replace('*','').replace('%','').strip()) and
                        (bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index].replace('%','')))))):
                iter_index += 1

                #printt('debug iter_index',iter_index,'text',text)
                if iter_index >max_iter:
                    break

                ignore_indices.append(nearest_index)
                nearest_index = get_nearest_index(data, ignore_indices)

            if all(d.isdigit() for d in data['text'][nearest_index].replace('.','').
                    replace('$','').replace('*','').replace('%','').strip()):
                try:
                    if float(data['text'][nearest_index].replace('$','').replace('*','').replace('%','').strip())<5000:
                        copay_entity_value = data['text'][nearest_index]
                        found_flag = True
                        break
                except:
                    # print('exception',data['text'][nearest_index].
                    #       replace('$','').replace('*','').replace('%','').strip())
                    pass

    #LOOP 2
    if not found_flag:
        for dindex, text in enumerate(data['text']):
            if any(t in text.lower() for t in ['amount','pay','cost','due']):
                ignore_indices = [dindex]
                iter_index = 0
                max_iter = 100

                # initalize with next number box
                nearest_index = dindex + 1
                while not bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index].replace('%', ''))):
                    nearest_index = nearest_index + 1

                # if box is too far off then inti with closest box
                if dist([data['left'][dindex] + (data['width'][dindex] / 2),
                         data['top'][dindex] + (data['height'][dindex] / 2)],
                        [data['left'][nearest_index] + (data['width'][nearest_index] / 2),
                         data['top'][nearest_index] + (data['height'][nearest_index] / 2)]) > 200:
                    nearest_index = get_nearest_index(data, ignore_indices)

                while (not (all(d.isdigit() for d in data['text'][nearest_index].replace('.', '').
                        replace('$', '').replace('*', '').replace('%', '').strip()) and
                            (bool(re.match('^(?=.*[0-9]$)', data['text'][nearest_index]))))):
                    iter_index += 1

                    if iter_index > max_iter:
                        break

                    ignore_indices.append(nearest_index)
                    nearest_index = get_nearest_index(data, ignore_indices)

                if all(d.isdigit() for d in data['text'][nearest_index].replace('.', '').
                        replace('$', '').replace('*', '').replace('%', '').strip()):
                    try:
                        if float(data['text'][nearest_index].
                                         replace('$', '').replace('*', '').replace('%', '').strip()) < 5000:
                            copay_entity_value = data['text'][nearest_index]
                            found_flag = True
                            break
                    except:
                        pass

    def find_amount(matches):

        numbers = []
        for match in matches:
            try:
                numbers.append(float(match.replace('$','').replace(',','').strip()))
            except:
                pass
        numbers_in_range=[n for n in numbers if (n>=10)]
        if not numbers_in_range:
            return ''
        return max(numbers_in_range)

    matches = re.findall('[$]+[\s]*[0-9.,]+', contents_tess)
    amount = find_amount(matches)
    amount_entity_value = ''
    try:
        if float(str(amount).replace('$','').replace('%',''))==float(copay_entity_value.replace('$','').replace('%','')):
            amount_entity_value = ''
        else:
            amount_entity_value = amount

    except:
        amount_entity_value = amount

    # # Ouptut JSON
    json_dict = {'Document': document_name.replace('_OCR', ''),
                 'Name': name_entity_value,
                 'Rx#': rx_entity_value,
                 'Drug Name': ', '.join(list(drug_name_entity_value)),
                 'NDC': ndc_entity_value,
                 'Filled Date': date_entity_value,
                 'Day Supply': supply_entity_value,
                 'Quantity': quantity_entity_value,
                 'Amount': amount_entity_value,
                 'Copay': copay_entity_value
                 }

    json_output = json.dumps(json_dict, indent=4, sort_keys=False)

    with open('./trailapp/json_outputs/'+json_dict['Document'][:-4]+'.json','w') as fd:
        fd.write(json_output)
