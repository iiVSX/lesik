import urllib3
import json
import os.path


def get_list_from_file(file_path):
    file_exists = os.path.exists(file_path)
    if not file_exists:
        return None
    f = open(os.getcwd() + "/" + file_path, 'r', encoding='utf-8')
    tmp_list = f.readlines()
    tmp_list = list(map(lambda elem: elem.replace("\n", ""), tmp_list))
    f.close()
    return tmp_list


def parse_tool_dict(file_path):
    file_exists = os.path.exists(file_path)
    if not file_exists:
        return None
    f = open(file_path, 'r', encoding='utf-8')
    delim = ">"
    tools = []
    tool_score_dict = {}
    for line in f.readlines():
        line = line.replace("\n", "")
        if delim in line:
            sp_line = line.split(delim)
            tool_score_dict[sp_line[0]] = sp_line[1]
            tools.append(sp_line[0])
        else:
            tools.append(line)
    f.close()
    return tools, tool_score_dict


def parse_cooking_act_dict(file_path):
    file_exists = os.path.exists(file_path)
    if not file_exists:
        return None
    f = open(file_path, 'r', encoding='utf-8')
    delim = ">"
    act_dict = {}
    act_score_dict = {}
    for line in f.readlines():
        line = line.replace("\n", "")
        if delim in line:
            sp_line = line.split(delim)
            act_dict[sp_line[0]] = sp_line[1]
            act_score_dict[sp_line[1]] = sp_line[2]
        else:
            act_dict[line] = line
    f.close()
    return act_dict, act_score_dict


def parse_act_to_tool_dict(file_path):
    file_exists = os.path.exists(file_path)
    if not file_exists:
        return None
    f = open(file_path, 'r', encoding='utf-8')
    delim = ">"
    t_delim = ","
    act_tool_dict = {}
    for line in f.readlines():
        line = line.replace("\n", "")
        if delim in line:
            sp_line = line.split(delim)
            act_tool_dict[sp_line[0]] = sp_line[1].split(t_delim)
    f.close()
    return act_tool_dict


def parse_idiom_dict(file_path):
    file_exists = os.path.exists(file_path)
    if not file_exists:
        return None
    f = open(file_path, 'r', encoding='utf-8')
    delim = ">"
    t_delim = ","
    sub_idiom_dict = {}
    for line in f.readlines():
        line = line.replace("\n", "")
        if delim in line:
            sp_line = line.split(delim)
            sub_idiom_dict[sp_line[0]] = sp_line[1].split(t_delim)
    f.close()
    return sub_idiom_dict


def parse_parenthesis(line):
    parenthesis_arr = line.split("(")
    ingredient = parenthesis_arr[0]
    volume = parenthesis_arr[1][0:-1]

    return ingredient, volume


def find_similarity(src, dst):
    similarity = 0
    if len(src) > len(dst):
        for d in dst:
            if d in src:
                similarity += 1
    else:
        for s in src:
            if s in dst:
                similarity += 1
    return similarity


def delete_bracket(text):
    while "(" in text and ")" in text:
        start = text.find('(')
        end = text.find(')')
        if end >= len(text) - 1:
            text = text[0:start]
        else:
            text = text[0:start] + " " + text[end + 1:len(text)]
        text = text.strip()

    return text


def merge_dictionary(src_dict, dst_dict):
    for key in src_dict.keys():
        if key in dst_dict and key in ['tool', 'ingre', 'seasoning', 'volume']:
            if src_dict.get(key):
                for value in src_dict.get(key):
                    if value not in dst_dict[key]:
                        dst_dict[key].append(value)


def mod_check(node, d_ele):
    add_ingre_list = []
    mod_result = None
    for d_element in d_ele['mod']:
        mod_node = node['dependency'][int(d_element)]
        # ?????????
        if mod_node['label'] == 'VP_MOD':
            mod_result = mod_node['text']
            for mod_element in mod_node['mod']:
                if node['dependency'][int(mod_element)]['label'] == 'VP':
                    mod_result = node['dependency'][int(mod_element)]['text'] + " " + mod_result
                    break
        else:
            # ?????? ????????? ?????? ??????
            if mod_node['label'] == 'NP_CNJ':
                add_ingre_list.append(mod_node['text'])
    return mod_result, add_ingre_list


# ??????????????? ?????? ??????
def volume_of_act(node, seq_list):
    for i in range(0, len(node['morp']) - 1):
        if node['morp'][i]['lemma'] == 'cm' or node['morp'][i]['lemma'] == '??????' or node['morp'][i]['lemma'] == '??????' or \
                node['morp'][i]['lemma'] == '??????':
            for seq in seq_list:
                if seq['start_id'] <= node['morp'][i]['id'] <= seq['end_id']:
                    seq['act'] = seq['act'] + "(" + node['morp'][i - 1]['lemma'] + node['morp'][i]['lemma'] + ")"
    return seq_list


# function
# ????????? ??????
def find_condition(node, seq_list):
    for srl in node['SRL']:
        s_arg = srl['argument']
        for s_ele in s_arg:
            if s_ele['type'] == "ARGM-CND":
                s_word_id = int(s_ele['word_id'])
                if node['dependency'][s_word_id]['label'] == 'VP':
                    act_plus_sentence = node['dependency'][s_word_id]['text']
                    mod_list = node['dependency'][s_word_id]['mod']
                    for mod in mod_list:
                        mod = int(mod)
                        if node['dependency'][mod]['label'] == 'VP_OBJ':
                            act_plus_sentence = node['dependency'][mod]['text'] + " " + act_plus_sentence
                        if node['dependency'][mod]['label'] == 'NP_SBJ':
                            act_plus_sentence = node['dependency'][mod]['text'] + " " + act_plus_sentence

                    for seq in seq_list:
                        word = node['word'][s_word_id]
                        begin = word['begin']
                        if seq['start_id'] <= begin <= seq['end_id']:
                            seq['act'] = "(" + act_plus_sentence + ")" + seq['act']

    return seq_list


def find_ingredient_dependency(node, seq_list, is_srl):
    remove_seq_list = []
    ingredient_modifier_dict = {}
    for i in range(0, len(seq_list)):
        is_etm = False
        is_cooking_act = False
        for m_ele in node['morp']:
            morp_id = m_ele['id']
            morp_type = m_ele['type']
            if morp_id < seq_list[i]['start_id'] or morp_id > seq_list[i]['end_id']:
                continue
            if morp_type == 'ETM':
                is_etm = True
                if morp_id > 0:
                    prev_morp = node['morp'][int(morp_id - 1)]
                    if prev_morp['type'] == 'VV' and prev_morp['lemma'] in cooking_act_dict:
                        is_cooking_act = True
                continue
            if is_etm and morp_type == 'NNG' and m_ele['lemma'] in seq_list[i]['ingre']:
                for w_ele in node['word']:
                    etm_id = morp_id - 1
                    if w_ele['begin'] <= etm_id <= w_ele['end']:
                        modified_ingredient = w_ele['text'] + " " + m_ele['lemma']
                        for j in range(0, len(seq_list[i]['ingre'])):
                            if m_ele['lemma'] == seq_list[i]['ingre'][j]:
                                if i not in ingredient_modifier_dict:
                                    ingredient_modifier_dict[i] = {}
                                ingredient_modifier_dict[i][j] = modified_ingredient
                                if is_cooking_act and i > 0:
                                    remove_seq_list.append(seq_list[i - 1])
            is_etm = False
            is_cooking_act = False

    if is_srl:
        for d_ele in node['dependency']:
            text = d_ele['text']
            for i in range(0, len(seq_list)):
                sequence = seq_list[i]
                for j in range(0, len(sequence['ingre'])):
                    original_ingredient = sequence['ingre'][j]
                    if original_ingredient in text:
                        mod_result, additional_ingredient_list = mod_check(node, d_ele)

                        # ?????????
                        if mod_result is not None:
                            modified_ingredient = mod_result + " " + original_ingredient
                            if i not in ingredient_modifier_dict:
                                ingredient_modifier_dict[i] = {}
                            if j not in ingredient_modifier_dict[i] or len(ingredient_modifier_dict[i][j]) < len(
                                    modified_ingredient):
                                ingredient_modifier_dict[i][j] = modified_ingredient

                            # ????????? ????????? ?????? ?????? (2?????? ??? ??? ???????????? ????????????, ???????????? ???????????? ???????????? ????????????)
                            if additional_ingredient_list and len(additional_ingredient_list) == 1:
                                for k in range(0, len(sequence['ingre'])):
                                    additional_ingredient = sequence['ingre'][k]

                                    # ???????????? ?????? ????????? ??? ?????? ????????? ????????? ????????? ????????? ?????? ????????? ??? ???????????? ????????????
                                    if j != k and additional_ingredient in additional_ingredient_list[0]:
                                        sequence['ingre'][k] = mod_result + " " + additional_ingredient

    for seq_id in ingredient_modifier_dict.keys():
        sequence = seq_list[seq_id]
        for ingredient_idx, modified_ingredient in ingredient_modifier_dict[seq_id].items():
            sequence['ingre'][ingredient_idx] = modified_ingredient

    for seq in remove_seq_list:
        seq_list.remove(seq)

    return seq_list


# ????????? ????????? ?????? ?????? ?????? ??????
def find_objective(node, seq_list):
    for dep in node['dependency']:
        if 'VP' in dep['label']:
            # ?????? ???????????? ???????????? ???????????? ??????????????? ???????????? ????????? ??????
            word_dep = node['word'][int(dep['id'])]
            start_id = word_dep['begin']
            end_id = word_dep['end']

            # ????????? ????????? ??????
            mod_list = dep['mod']
            for mod in mod_list:
                mod_dep = node['dependency'][int(mod)]
                if "OBJ" in mod_dep['label']:
                    word = node['word'][int(mod_dep['id'])]
                    end = word['end']
                    for i in range(0, len(seq_list)):
                        sequence = seq_list[i]
                        if sequence['start_id'] <= end <= sequence['end_id'] and start_id <= sequence[
                            'end_id'] <= end_id:
                            is_objective = True
                            for ingre in sequence['ingre']:
                                if ingre in word['text']:
                                    is_objective = False
                                    break
                            if is_objective:
                                for seasoning in sequence['seasoning']:
                                    if seasoning in word['text']:
                                        is_objective = False
                                        break

                            if is_objective:
                                sequence['act'] = word['text'] + " " + sequence['act']
    return seq_list


# ????????????5
# ????????? ???????????? ??????????????? ??????
def find_adverb(node, sequence_list):
    for m_ele in node['morp']:
        m_id = int(m_ele['id'])
        if m_id == 0:
            continue
        prev_morp = node['morp'][m_id - 1]
        if m_ele['type'] == 'VV' and m_ele['lemma'] in cooking_act_dict and prev_morp['type'] == "JKB":
            for i in range(0, len(sequence_list)):
                sequence = sequence_list[i]
                if sequence['start_id'] <= m_id <= sequence['end_id']:
                    for w_ele in node['word']:
                        w_begin = int(w_ele['begin'])
                        w_end = int(w_ele['end'])
                        if w_begin <= int(prev_morp['id']) <= w_end:
                            chk_morp_list =  node['morp'][w_begin:w_end+1]
                            for chk_morp in chk_morp_list:
                                for j in range(0, len(sequence['ingre'])):
                                    if chk_morp['lemma'] in sequence['ingre'][j]:
                                        sequence['ingre'].remove(sequence['ingre'][j])
                                for k in range(0, len(sequence['seasoning'])):
                                    if chk_morp['lemma'] in sequence['seasoning'][k]:
                                        sequence['seasoning'].remove(sequence['seasoning'][k])
                            sequence_list[i]['act'] = node['word'][int(w_ele['id'])]['text'] + " " + sequence_list[i]['act']
    
    return sequence_list


# ????????????4
# ?????????, ???????????? ??????
def select_cooking_zone(sequence_list):
    score_board = []
    period_check = []
    for i in range(0, len(sequence_list)):
        act_fire_score = 0.0
        tool_fire_score = 0.0
        if sequence_list[i]['act'] in zone_dict['act'].keys():
            act_fire_score = float(zone_dict['act'].get(sequence_list[i]['act']))
        for tool in sequence_list[i]['tool']:
            if tool in zone_dict['tool'].keys():
                tool_fire_score = float(zone_dict['tool'].get(tool))

        score_board.append(act_fire_score + tool_fire_score)
        if score_board[i] >= 0.7:
            sequence_list[i]['zone'] = "?????????"
        else:
            sequence_list[i]['zone'] = "????????????"
    '''
        if sequence_list[i]['sentence'][-1] == '.' or sequence_list[i]['sentence'][-3] == '.':
            period_check.append(True)
        else:
            period_check.append(False)

    
    keep_i = -1
    while keep_i != len(sequence_list[i] - 1):
        for i in range(keep_i + 1, len(sequence_list)):
            if period_check[i] == False:
                if score_board[i] >= 0.2:
                    sequence_list[i]['zone'] = "?????????"
            elif period_check[i] == True:
                keep_i = i
                break
    '''
    return sequence_list


# ?????? ????????? ?????? ?????? ??????
def verify_etn(node, seq_list):
    remove_seq_list = []
    for morp in node['morp']:
        if morp['type'] == 'ETN':
            morp_id = int(morp['id'])
            if morp_id > 0:
                prev_morp = node['morp'][morp_id - 1]
                if prev_morp['type'] == 'VV' and prev_morp['lemma'] in cooking_act_dict:
                    for seq_id in range(0, len(seq_list)):
                        sequence = seq_list[seq_id]
                        if sequence['start_id'] <= morp_id <= sequence['end_id']:
                            remove_seq_list.append(sequence)
                            if seq_id < len(seq_list) - 1:
                                next_sequence = seq_list[seq_id + 1]
                                if next_sequence['act'] == '???':
                                    merge_dictionary(sequence, next_sequence)
                                    next_sequence['start_id'] = sequence['start_id']

    for sequence in remove_seq_list:
        seq_list.remove(sequence)

    return seq_list


def find_omitted_ingredient(node, seq_list, ingredient_dict):
    critical_type_list = ['ARG0', 'ARG1']
    for sequence in seq_list:
        if not sequence['ingre']:
            for srl in node['SRL']:
                s_arg = srl['argument']
                s_word = node['word'][int(srl['word_id'])]
                if srl['verb'] == sequence['act'] and sequence['start_id'] <= s_word['begin'] <= sequence['end_id']:
                    for s_ele in s_arg:
                        s_text = s_ele['text']
                        s_type = s_ele['type']
                        if s_type in critical_type_list:
                            for ingredient in ingredient_dict.keys():
                                if ingredient in s_text and ingredient not in sequence['ingre'] and ingredient not in \
                                        sequence['seasoning']:
                                    sequence['ingre'].append(ingredient)
    return seq_list


def remove_redundant_sequence(node, seq_list):
    is_redundant = False
    del_seq_list = []
    critical_type_dict = {'NNG', 'NNP', 'VA', 'XPN', 'SP'}

    for morp in node['morp']:
        if morp['type'] == 'VV' and is_redundant is False:
            # ???????????? ?????? ????????? ??????
            if morp['lemma'] in cooking_act_dict:
                continue
            next_morp_id = int(morp['id']) + 1
            if next_morp_id == len(node['morp']):
                continue
            
            next_morp = node['morp'][next_morp_id]
            if next_morp['type'] == 'EC':
                is_redundant = True
                continue

        if is_redundant:
            # ???????????? ?????? ?????? ?????? ?????? ????????? ????????? ??????
            if morp['type'] == 'EC':
                continue
            elif morp['type'] in critical_type_dict:
                is_redundant = False
                continue
            else:
                # ???????????? ?????? ????????? ???????????? ????????? ??????
                morp_id = morp['id']
                for i in range(1, len(seq_list)):
                    # ?????? ???????????? ????????? ???????????? ?????? ?????? ???????????? ??????
                    if seq_list[i]['start_id'] <= morp_id <= seq_list[i]['end_id']:
                        merge_dictionary(seq_list[i - 1], seq_list[i])
                        seq_list[i]['start_id'] = seq_list[i - 1]['start_id']
                        if seq_list[i - 1] not in del_seq_list:
                            del_seq_list.append(seq_list[i - 1])
                        is_redundant = False
                        break

    # ???????????? ????????? ??????
    for seq in del_seq_list:
        seq_list.remove(seq)

    return seq_list


def verify_coref(coref_dict, node, word_id):
    word = node['word'][word_id]['text']
    coref_keyword_list = ['??????', '??????', '??????', '??????', '??????']
    for keyword in coref_keyword_list:
        if keyword in word:
            coref_cand_list = []
            for coref_key in coref_dict.keys():
                if coref_key == '????????????':
                    continue
                if keyword in coref_key and coref_dict[coref_key] != {}:
                    coref_cand_list.append(coref_key)

            coref_cand = None
            if len(coref_cand_list) >= 1:
                if word_id > 0:
                    prev_word = node['word'][word_id - 1]['text']
                    max_similarity = 0.0

                    for cand in coref_cand_list:
                        comp_word = cand.replace(keyword, "").strip()
                        similarity = find_similarity(comp_word, prev_word)
                        if similarity > max_similarity:
                            coref_cand = cand

            if coref_cand is not None:
                coref_ingredient_dict = coref_dict[coref_cand]
                if coref_ingredient_dict != {}:
                    coref_dict[coref_cand] = {}
                    return coref_ingredient_dict
                return {coref_cand: ""}


def create_sequence(node, coref_dict, ingredient_dict, ingredient_type_list, entity_mode, is_srl):
    # ??? ??????
    seq_list = []

    # ????????? ????????? ?????? ?????? ??????
    prev_seq_id = -1
    for m_ele in node['morp']:
        if m_ele['type'] == 'VV':
            act_id = int(m_ele['id'])
            if node['morp'][act_id + 1]['type'] == 'ETM' and node['morp'][act_id + 2]['lemma'] != '???':
                continue
            act = m_ele['lemma']

            # ?????? ?????? ??????
            if act in cooking_act_dict:
                # ????????? ????????? 6?????? ??????
                seq_dict = {'cond': "", 'act': act, 'tool': [], 'ingre': [], 'seasoning': [], 'volume': [],
                            'zone': "", "start_id": prev_seq_id + 1, "end_id": act_id, "sentence": ""}

                # co-reference ??? dictionary??? ?????? word?????? ?????? ??????
                for w_ele in node['word']:
                    if w_ele['begin'] <= prev_seq_id:
                        continue
                    if w_ele['end'] > act_id:
                        break

                    # co-reference ??????
                    sub_ingredient_dict = verify_coref(coref_dict, node, int(w_ele['id']))
                    if sub_ingredient_dict is not None:
                        for key, value in sub_ingredient_dict.items():
                            if len(value) != 0:
                                seq_dict['seasoning'].append(key + "(" + value + ")")
                            else:
                                seq_dict['seasoning'].append(key)

                    # ?????? ?????? ??????
                    for t_ele in tool_list:
                        if t_ele in w_ele['text']:
                            seq_dict['tool'].append(t_ele)

                    # ????????? ??????
                    seasoning = ""
                    for s_ele in seasoning_list:
                        if s_ele in w_ele['text']:
                            if len(s_ele) > len(seasoning):
                                seasoning = s_ele

                    if seasoning != "" and seasoning not in seq_dict['seasoning'] and seasoning not in ingredient_dict.keys():
                        seq_dict['seasoning'].append(seasoning)

                    # ????????? ??????
                    ingredient = ""
                    for i_ele in ingredient_dict:
                        if i_ele in w_ele['text']:
                            if len(i_ele) > len(ingredient):
                                ingredient = i_ele
                    if ingredient != "" and ingredient not in seq_dict['seasoning'] and ingredient not in seq_dict[
                        'ingre']:
                        seq_dict['ingre'].append(ingredient)

                # ?????? ?????? ?????? ?????? ?????? ?????? ??? ?????? ???????????? ?????? ??????
                if seq_dict['tool'] == [] and act in act_to_tool_dict:
                    seq_dict['tool'] = act_to_tool_dict[act]

                seq_list.append(seq_dict)
                prev_seq_id = act_id

    # ????????? ????????? ????????? ???????????? ?????? ??????
    if entity_mode == 'kobert':
        for sequence in seq_list:
            for ne in node['NE']:
                if ne['type'] in ingredient_type_list and ne['begin'] >= sequence['start_id'] and ne['end'] < \
                        sequence['end_id']:
                    # ???????????? ????????? ?????? ??????
                    if ne['text'] not in sequence['ingre']:
                        if ne['text'] in seasoning_list:
                            break

                        # ????????? ????????? ?????? ????????? ????????? ????????? ?????? ??????
                        sub_ord_ingredient_list = []
                        for ingredient in sequence['ingre']:
                            if ingredient in ne['text']:
                                sub_ord_ingredient_list.append(ingredient)

                        for ingredient in sub_ord_ingredient_list:
                            sequence['ingre'].remove(ingredient)

                        sequence['ingre'].append(ne['text'])

    # ???????????? ????????? ?????? ??? ?????? ???????????? ??????
    sequence_list = remove_redundant_sequence(node, seq_list)

    if is_srl:
        # ?????? ???????????? ????????? ????????? ??????
        sequence_list = find_omitted_ingredient(node, sequence_list, ingredient_dict)

        # ????????????(??????)
        # sequence_list = volume_of_act(node, sequence_list)
        # ???????????? ??????
        sequence_list = verify_etn(node, sequence_list)

    for sequence in sequence_list:
        sequence['act'] = cooking_act_dict[sequence['act']]

    if is_srl:
        # ???????????? ????????? ?????? ?????? ?????? ??????
        sequence_list = find_objective(node, sequence_list)

        # ????????? ??????
        sequence_list = find_ingredient_dependency(node, sequence_list, is_srl)

        # ????????? ??????????????????
        sequence_list = find_condition(node, sequence_list)
    
    # sentence ??????
    sequence_list = find_sentence(node, sequence_list)

    # ?????????/???????????? ??????
    sequence_list = select_cooking_zone(sequence_list)
    
    # ????????? ???????????? ????????? ??????
    sequence_list = find_adverb(node, sequence_list)

    return sequence_list


def extract_ingredient_from_kobert(node_list):
    kobert_api_url = "http://ec2-54-180-98-174.ap-northeast-2.compute.amazonaws.com:5000"
    recipe_text = "\n".join(list(map(lambda node: node['text'], node_list)))

    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        kobert_api_url,
        headers={"Content-Type": "application/text; charset=UTF-8"},
        body=recipe_text.encode('utf-8')
    )

    json_object = json.loads(response.data)

    kobert_pre_ingre_dict = json_object.get("pre_ingre_dict")
    kobert_ingredient_list = kobert_pre_ingre_dict.get("ingredient")
    kobert_seasoning_list = kobert_pre_ingre_dict.get("seasoning")

    ingredient_dict = {}
    for line in kobert_ingredient_list:
        ingredient, volume = parse_parenthesis(line)
        if volume is None:
            volume = ""

        if ingredient is not None:
            ingredient_dict[ingredient] = volume

    for line in kobert_seasoning_list:
        seasoning, volume = parse_parenthesis(line)
        if volume is None:
            volume = ""
        if seasoning is not None:
            ingredient_dict[seasoning] = volume
            seasoning_list.append(seasoning)

    return ingredient_dict, seasoning_list


def extract_ingredient_from_node(ingredient_type_list, volume_type_list, node):
    volume_node = None
    ingredient_list = []

    for ne in node['NE']:
        if ne['type'] in volume_type_list:
            volume_node = ne
        if ne['type'] in ingredient_type_list:
            if volume_node is not None and ne['begin'] < volume_node['end']:
                continue
            ingredient_list.append(ne)

    for word in node['word']:
        for volume in volume_list:
            if volume in word['text']:
                volume_node = word

    sub_ingredient_dict = {}
    if volume_node is not None:
        sub_ingredient_dict = {ne['text']: volume_node['text'] for ne in ingredient_list}

    return sub_ingredient_dict


def parse_node_section(entity_mode, is_srl, node_list):
    coref_dict = {}
    volume_type_list = ["QT_SIZE", "QT_COUNT", "QT_OTHERS", "QT_WEIGHT", "QT_PERCENTAGE"]
    ingredient_type_list = ["CV_FOOD", "CV_DRINK", "PT_GRASS", "PT_FRUIT", "PT_OTHERS", "PT_PART", "AM_FISH",
                            "AM_OTHERS"]
    ingredient_dict = {}
    sequence_list = []
    is_ingredient = True
    sub_type = None
    remove_node_list = []

    if entity_mode == "kobert":
        ingredient_dict, kobert_seasoning_list = extract_ingredient_from_kobert(node_list)

        if not kobert_seasoning_list:
            seasoning_list.extend(kobert_seasoning_list)

    is_tip = False
    for node in node_list:
        if "[" in node['text'] and "]" in node['text']:
            sub_type = node['text'][1:-1].replace(" ", "")
            if sub_type == '????????????':
                is_ingredient = False
            else:
                coref_dict[sub_type] = {}
            continue
        if is_ingredient:
            if entity_mode == 'kobert':
                continue
            else:
                sub_ingredient_dict = extract_ingredient_from_node(ingredient_type_list, volume_type_list, node)
                if sub_type is not None:
                    coref_dict[sub_type].update(sub_ingredient_dict)
                ingredient_dict.update(sub_ingredient_dict)
        else:
            node['text'] = node['text'].strip()
            if is_tip and node['text'][0].isdigit() == False and node['text'][1] == '.':
                remove_node_list.append(node)
                continue
            else:
                is_tip = False    
                # tip ?????? ???????????? ?????????
                if len(node['text']) == 0 or "tip" in node['text'].lower():
                    remove_node_list.append(node)
                    is_tip = True
                    continue
                else:
                    node['text'] = delete_bracket(node['text'])

                    if len(node['text']) == 0:
                        remove_node_list.append(node)
                        continue

            sequence = create_sequence(node, coref_dict, ingredient_dict, ingredient_type_list, entity_mode, is_srl)
            if not sequence:
                remove_node_list.append(node)

            for seq_dict in sequence:
                for ingre in seq_dict['ingre']:
                    if ingre in ingredient_dict:
                        seq_dict['volume'].append(ingredient_dict.get(ingre))
                sequence_list.append(seq_dict)

    for node in remove_node_list:
        node_list.remove(node)
    return sequence_list


def find_sentence(node, sequence_list):
    prev_seq_id = 0
    for i in range(0, len(sequence_list)):
        if sequence_list[i]['sentence'] != "":
            continue
        start_id = sequence_list[i]['start_id']
        end_id = sequence_list[i]['end_id']
        if start_id < prev_seq_id:
            break

        next_seq_id = 0
        if i < len(sequence_list) - 1:
            next_seq_id = sequence_list[i + 1]['start_id']

        word_list = []
        extra_word_list = []
        for w_ele in node['word']:
            text = w_ele['text']
            begin = w_ele['begin']
            end = w_ele['end']
            if start_id <= begin <= end_id:
                word_list.append(text)
            else:
                if end_id < end:
                    if next_seq_id < end_id or end < next_seq_id:
                        if not extra_word_list:
                            extra_word_list.append("(")
                        extra_word_list.append(text)

        sequence_list[i]['sentence'] = " ".join(word_list)
        sequence_list[i]['sentence'] = delete_bracket(sequence_list[i]['sentence'])
        if extra_word_list:
            extra_word_list.append(")")
            sequence_list[i]['sentence'] += " ".join(extra_word_list)
        prev_seq_id = sequence_list[i]['end_id']

    return sequence_list


def main():
    # static params
    open_api_url = "http://aiopen.etri.re.kr:8000/WiseNLU"
    access_key = "0714b8fe-21f0-44f9-b6f9-574bf3f4524a"
    # access_key = "84666b2d-3e04-4342-890c-0db401319568"
    analysis_code = "SRL"

    # recipe extraction
    file_path = input("????????? ?????? ????????? ????????? ????????? : ")
    f = open(file_path, 'r', encoding="utf-8")
    original_recipe = str.join("\n", f.readlines())

    entity_mode = input("????????? ?????? ????????? ????????? ????????? (1 : ETRI, 2 : ko-BERT) : ")
    is_srl = input("SRL on/off??? ????????? ????????? (1 : OFF, 2 : ON) : ")
    if entity_mode == '1':
        entity_mode = 'etri'
    else:
        entity_mode = 'kobert'

    if is_srl == '1':
        is_srl = False
    else:
        is_srl = True

    f.close()

    # get cooking component list & dictionary from files
    global seasoning_list, volume_list, time_list, temperature_list, cooking_act_dict, act_to_tool_dict, tool_list, idiom_dict, zone_dict
    if entity_mode != 'kobert':
        seasoning_list = get_list_from_file("labeling/seasoning.txt")
    volume_list = get_list_from_file("labeling/volume.txt")
    time_list = get_list_from_file("labeling/time.txt")
    temperature_list = get_list_from_file("labeling/temperature.txt")
    cooking_act_dict, act_score_dict = parse_cooking_act_dict("labeling/cooking_act.txt")
    act_to_tool_dict = parse_act_to_tool_dict("labeling/act_to_tool.txt")
    tool_list, tool_score_dict = parse_tool_dict("labeling/tool.txt")
    idiom_dict = parse_idiom_dict("labeling/idiom.txt")

    zone_dict = {'act': act_score_dict, 'tool': tool_score_dict}

    # ETRI open api
    request_json = {
        "access_key": access_key,
        "argument": {
            "text": original_recipe,
            "analysis_code": analysis_code
        }
    }

    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        open_api_url,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        body=json.dumps(request_json)
    )

    json_object = json.loads(response.data)
    node_list = json_object.get("return_object").get("sentence")
    sequence_list = parse_node_section(entity_mode, is_srl, node_list)

    print(str(json.dumps(sequence_list, ensure_ascii=False)))


if __name__ == "__main__":
    main()