import pyodbc
import json 

app = Flask(__name__)

@app.route('/teste', methods=['GET'])
def soma():
    return '<p> Teste </p>'


@app.route('/recommend_courses', methods=['POST'])
def recommend():

    data = json.loads(request.data)

    # # Teste simples
    # return 'Abc'

    #-----------------REQUISIÇÃO------------------------------------------------

    # Realizando a busca e cruzando dados
    base64str, return_df = recommend_courses(data)
    
    return {'img':'data:image/png;base64,'+str(base64str), 'table':return_df.to_json(orient='records',force_ascii=False)}



@app.route('/recommend_courses_auto', methods=['POST'])
def recommend2():

    data = json.loads(request.data)

    # # Teste simples
    # return 'Abc'

    #-----------------REQUISIÇÃO------------------------------------------------

    # Realizando a busca e cruzando dados
    base64str = recommend_courses_auto(data)
    
    return {'img':'data:image/png;base64,'+str(base64str)}



#By DataMaster

from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpBinary
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
from statistics import mode
from itertools import chain
from io import BytesIO
from PIL import Image
import pandas as pd
import numpy as np
import difflib
import base64
import time
import ast


# Join de DFs por similaridade de Strings

# Objetivo: Junção interna de dois DataFrames usando a biblioteca difflib em Python, 
# combinando colunas de texto com base na similaridade mais próxima.

# Entrada: Duas tuplas segundo o padrão: (df1,text_column1), (df2,text_column2)

# Saída: Crie um novo DataFrame com pares de texto correspondentes de c1 e c2, onde cada par tem a correspondência textual mais próxima entre as duas listas.


def inner_join_by_str_match(tuple_df1, tuple_df2):

    df1 = tuple_df1[0]
    text_col1 = tuple_df1[1]

    df2 = tuple_df2[0]
    text_col2 = tuple_df2[1]

    # Check if the text column name already exists in df2
    if text_col2 in df1.columns:
        # Rename the text column in df2 to ensure uniqueness
        text_col2 = text_col2 + "_df2"
        df2 = df2.rename(columns={tuple_df2[1]: text_col2})

    # Initialize a dictionary to store matches
    matches = {}

    # Initialize a set to keep track of matched indices in df2
    matched_indices = set()

    # Iterate through the elements in df1
    for index, row in df1.iterrows():
        c1_text = row[text_col1]
        closest_match = None

        # Iterate through df2 to find the closest match that has not been used
        for j, c2_row in df2.iterrows():
            if j not in matched_indices:
                c2_text = c2_row[text_col2]
                potential_match = difflib.get_close_matches(c1_text, [c2_text], n=1, cutoff=0.6)
                if potential_match:
                    closest_match = potential_match[0]
                    matched_indices.add(j)
                    break  # Stop searching for a match once one is found

        if closest_match:
            matches[c1_text] = closest_match

    # Create a new DataFrame with the matches and all columns from both DataFrames
    result_df = pd.DataFrame(matches.items(), columns=[text_col1, text_col2])

    # Merge additional columns from the input DataFrames
    result_df = pd.merge(result_df, df1, left_on=text_col1, right_on=text_col1, how='inner')
    result_df = pd.merge(result_df, df2, left_on=text_col2, right_on=text_col2, how='inner')

    # Print the result
    return result_df


def recommend_courses(forms_data):
    
    # Essa é uma variável para quando se quer simula no jupyter notebook, marque 0 para prod
    notebook = 0

    start = time.time()

    #Leitura direto do Arquivo mastigado do jeffs (Escola de negócios)

    xl = pd.ExcelFile(r"CHA.xlsx")

    CFs_cursos = []

    # Itera sobre cada planilha
    for i, nome_planilha in enumerate(xl.sheet_names):

        cols = {}
        df = xl.parse(nome_planilha).fillna('')

        for c in df.columns:
            cols = cols|{c : [v.strip() for v in list(df[c]) if len(v)>1]}

        cols = cols|{'CF_COMPLETO' : list(chain.from_iterable(list(cols.values())))}

        CFs_cursos.append({'Curso': nome_planilha, 'Código_do_Produto':'JTD-{}'.format(i+1), 'Conteúdo_formativo': cols})

    xl.close()

    CFs_cursos = pd.DataFrame(CFs_cursos)
    #display(CFs_cursos)



    # Aqui vou definir as categorias de cada curso, para ajudar na fomração do Radar

    categorias = {'Vendas' : ['JTD-1','JTD-2','JTD-3'], 

     'Gestão de Pessoas': ['JTD-4','JTD-5','JTD-6','JTD-7','JTD-8','JTD-9'],

     'Marketing':['JTD-10','JTD-11'], 

     'Estratégia': ['JTD-12','JTD-13','JTD-15'],

     'Finanças': ['JTD-14','JTD-16']}

    #print(categorias)

    CFs_cursos["Cat"] = [k for c in CFs_cursos['Código_do_Produto'] for k,v in categorias.items() if c in v]
    #display(CFs_cursos)


    # ============ FORMS ============================

    # Agora vou ler o retorno do Forms para avaliar as categorias

    df_quest_flag = pd.read_excel(r"db_questoes_assessment.xlsx")

    df_quest_flag = df_quest_flag[df_quest_flag["Nível da Questão"]=="Nível 3"]


    # import random
    # # Criando uma potnuação exemlpo para Acertos e Erros
    # # Define the ratio of 1s and 0s
    # ratio_1s = 0.80
    # ratio_0s = 0.20
    # df_quest_flag['Pontuação'] = [random.choices([0, 1], [ratio_0s, ratio_1s])[0] for _ in df_quest_flag['CAPACIDADE TÉCNICA Relacionada']]


    # ====================================================
    # LENDO DADOS DO FOMRS

    # Dados de entrada da API:

    d1 = forms_data['d1']
    d2 = forms_data['d2']
    d3 = forms_data['d3']

    # Manipulação e preparo

    d1 = d1.replace('false', 'False').replace('true', 'True')
    d2 = d2.replace('false', 'False').replace('true', 'True')
    d3 = d3.replace('false', 'False').replace('true', 'True')


    d1 = ast.literal_eval(d1) # {Texto_Questão_Forms: ID_Questão_Forms ...}
    d2 = ast.literal_eval(d2) # {'responder': Email, 'submitDate':data_resposta}|{ID_Questão_Forms: Texto_Alternativa_selecionada}
    d3 = ast.literal_eval(d3) # lista de alternativas e respostas corretas do forms # {'QuestionID': ID_Questão_Forms, 'Choices': [{'FormsProDisplayRTText': Texto_Alternativa,'IsAnswerKey': True ou False}, ...}


    # Chave do email, que deve ser desconsiderada
    # d2: key 'raf7bbe5423dd43bb808bdde2b1ea053b'                
    # d3: "QuestionID":'raf7bbe5423dd43bb808bdde2b1ea053b'  

    # Parsing --------------------------------

    questions = {k:v for k,v in d1.items() if v not in ['raf7bbe5423dd43bb808bdde2b1ea053b']}

    # Dicionaário D2 {ID_Questão: Texto_Alternativa_selecionada ...}
    user_answers = {k:v for k,v in d2.items() if k not in ['responder','submitDate','raf7bbe5423dd43bb808bdde2b1ea053b']}

    # Criando o dicionário de {'ID_Questão_Forms':Texto_Alternativa_Correta}
    real_answers = {}

    for q in d3:
        if q['QuestionID'] not in ['raf7bbe5423dd43bb808bdde2b1ea053b']:
            for c in q['Choices']:
                if 'IsAnswerKey' not in c.keys():
                    #print(c)
                    pass
                else:
                    if c['IsAnswerKey']==True:
                        real_answers = real_answers|{q['QuestionID']:c['FormsProDisplayRTText']}

    
    # Criando um Dataframe Pandas

    forms_df = pd.DataFrame(columns=['Texto_Questão_Forms','ID_Questão_Forms','Texto_Alternativa_selecionada','Texto_Alternativa_Correta'])

    forms_df[['Texto_Questão_Forms','ID_Questão_Forms']] = list(questions.items())

    forms_df['Texto_Alternativa_selecionada'] = [user_answers[id_q] for id_q in forms_df['ID_Questão_Forms']]

    forms_df['Texto_Alternativa_Correta'] = [real_answers[id_q] for id_q in forms_df['ID_Questão_Forms']]

    forms_df['Pontuação'] = [1 if s==c else 0 for s,c in forms_df[['Texto_Alternativa_selecionada','Texto_Alternativa_Correta']].values.tolist()]

    # display(forms_df)


    # ---------------------------------------
    # Merge com os dados reais do FORMS

    df_quest_flag = inner_join_by_str_match((df_quest_flag,'Título da Questão/Pergunta'), (forms_df,'Texto_Questão_Forms'))

    df_quest_flag['Cat'] = [k for c in df_quest_flag['Código_do_Produto'] for k,v in categorias.items() if c in v]
    #display(df_quest_flag)



    
    def radar_chart(dataframe, category_col, score_col):

        # Aggregating and summarizing by Categories and values for the Radar
        df = dataframe.groupby([category_col], as_index=False).agg({score_col:'mean'})

        """Create a radar chart of N categories, depending on how many rows the DataFrame has."""

        # Calculate the theta values
        theta = np.linspace(0, 2 * np.pi, len(df), endpoint=False)

        # Close the plot
        radii = df[score_col].tolist()
        radii += radii[:1]
        theta = np.append(theta, theta[0])

        # Create the radar chart
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})

        # Plot the edges of the area
        ax.fill(theta, radii, 'r', alpha=0.1)
        ax.plot(theta, radii, color='r', linewidth=2)

        # Place dots at the vertices
        ax.plot(theta[:-1], radii[:-1], 'ro', markersize=5)

        # Set the axis labels
        ax.set_xticks(theta[:-1])

        # Set the radar chart axis limits to ensure a fixed scale from 0 to 1
        ax.set_ylim(0, 1)

        # Customize the radius for the x-axis tick labels to move them further away
        radius_custom = -0.15  # Adjust this value for the desired distance
        ax.set_xticklabels(df[category_col], fontsize=12, va='center', position=(0, radius_custom))


        # Remove radial labels
        ax.set_yticklabels([])

        # Add data labels (values) on top of each radar point with an offset for readability
        for i, (x, y) in enumerate(zip(theta[:-1], radii[:-1])):
            offset = 0.15  # Adjust this value for the desired offset
            ax.text(x, y + offset, f'{y*100:.1f}%', fontsize=11, ha='center', va='bottom', color='r')


        # Set the title
        ax.set_title('Radar Assessment', y=1.2)

        # Add a label indicating the scale in the bottom right corner outside the chart
        ax.text(1.3, -0.2, 'Scale: 0-100%', fontsize=12, ha='right', va='bottom', color='r', transform=ax.transAxes)


        return fig, ax


    # Create the radar chart
    fig, ax = radar_chart(df_quest_flag, category_col='Cat', score_col='Pontuação')
    
    if notebook!=0:
        # Show the chart
        plt.show()

        # Save the chart as a PNG file (not needed)
        plt.savefig('radar_chart.png', format='png')
    
    
    # Save the chart as a PNG file in memory (BytesIO)
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convert the image in memory to a base64 string
    base64str = base64.b64encode(buffer.read()).decode('utf-8')



    # ==================================================================================
    #==========="DESSOMBREAMENTO" DE CONTEÚDO FORMATIVO ================================

    # -----------------------------------------------------
    # Identifica padrões similares e clusteriza
    def group_strings(strings, similarity_threshold=0.7):
        groups = []

        def is_similar(str1, str2):
            return SequenceMatcher(None, str1.lower(), str2.lower()).ratio() >= similarity_threshold

        for string in strings:
            added = False
            for group in groups:
                if any(is_similar(string, s) for s in group):
                    group.append(string)
                    added = True
                    break
            if not added:
                groups.append([string])

        return groups
    # -----------------------------------------------------

    # Aqui listamos Capacidades Técnicas, Socioemocionais e Conhecimentos de todos os planos de curso em análise


    # CFs_cursos é um dataframe formado de uma lista de dicionários

    # CFs_cursos = pd.DataFrame([
    #     {'Curso': 'NOME DO CURSO',
    #      'Código_do_Produto': 'CÓDIGO'
    #     'Conteúdo_formativo':
    #      {
    #         'Capacidades_técnicas': [lista de capacidades tec],
    #         'Capacidades_socioemocionais': [lista de capacidades soc],
    #         'Conhecimentos': [lista de conhecimentos],
    #         'CF_COMPLETO': [lista com todos os elementos do conteúdo sem separar por tec, soc, ou conh]
    #      }
    #     },
    #     ...
    #    ])


    # # ============== SOMBREAMENTO CLASSIFICADO =============================
    # # Identificando o sombreamento de Capacidades Técnicas, Socioemocionais e Conhecimentos
    # cap_tec = list(chain.from_iterable([c['Capacidades_técnicas'] for c in CFs_cursos['Conteúdo_formativo']]))
    # cap_soc = list(chain.from_iterable([c['Capacidades_socioemocionais'] for c in CFs_cursos['Conteúdo_formativo']]))
    # conhec = list(chain.from_iterable([c['Conhecimentos'] for c in CFs_cursos['Conteúdo_formativo']]))



    # Identificando o sombreamento GERAL do Conteúdo Formativo
    cf_geral = list(chain.from_iterable([c['CF_COMPLETO'] for c in CFs_cursos['Conteúdo_formativo']]))

    somb = [s for s in group_strings(cf_geral, similarity_threshold=0.85) if len(s) > 1]


    # Mapeamento de cursos e códigos de produtos para sombreamentos
    mapeamento_sombreamentos = []

    for sombreamento in somb:
        cursos_sombreamento = []
        codigos_sombreamento = []

        for index, row in CFs_cursos.iterrows():
            curso = row['Curso']
            codigo = row['Código_do_Produto']


    # # ============== SOMBREAMENTO CLASSIFICADO =============================
    #         capacidades_tecnicas = row['Conteúdo_formativo']['Capacidades_técnicas']
    #         # Verifica se alguma capacidade técnica do curso está no sombreamento
    #         if any(c in sombreamento for c in capacidades_tecnicas):
    #             cursos_sombreamento.append(curso)
    #             codigos_sombreamento.append(codigo)

    #         capacidades_socioemocionais = row['Conteúdo_formativo']['Capacidades_socioemocionais']
    #         # Verifica se alguma capacidade técnica do curso está no sombreamento
    #         if any(c in sombreamento for c in capacidades_socioemocionais):
    #             cursos_sombreamento.append(curso)
    #             codigos_sombreamento.append(codigo)

    #         conhecimentos = row['Conteúdo_formativo']['Conhecimentos']
    #         # Verifica se alguma capacidade técnica do curso está no sombreamento
    #         if any(c in sombreamento for c in conhecimentos):
    #             cursos_sombreamento.append(curso)
    #             codigos_sombreamento.append(codigo)
    # =========================================================================

            topicos_formativos = row['Conteúdo_formativo']['CF_COMPLETO']

            # Verifica se algum tópico formativo do curso está no sombreamento
            if any(t in sombreamento for t in topicos_formativos):
                cursos_sombreamento.append(curso)
                codigos_sombreamento.append(codigo)

        if len(codigos_sombreamento)>1: #(Se não sombreou internamente)
            sombreamento_str = mode(sombreamento)
            mapeamento_sombreamentos.append({'tópico_formativo': sombreamento_str, 'sombreamento':sombreamento, 'Cursos': cursos_sombreamento, 'Códigos_de_Produto': codigos_sombreamento})


    df_sombreamentos = pd.DataFrame(mapeamento_sombreamentos)
    # display(df_sombreamentos)


    # ========================================================

    # Adicionando todos os Tópicops Formativos do Best Guess, do primeiro curso recomendado

    # Inicialize um DataFrame vazio para armazenar os resultados de todos os cursos
    df_itens_nao_sombreados = pd.DataFrame(columns=['tópico_formativo', 'sombreamento', 'Cursos', 'Códigos_de_Produto'])

    # Itera sobre todas as linhas do DataFrame CFs_cursos
    for _, row in CFs_cursos.iterrows():
        itens_curso = row['Conteúdo_formativo']['CF_COMPLETO']

        # Filtra os itens que não estão sombreados
        itens_nao_sombreados = [item for item in itens_curso if item not in set(list(chain.from_iterable(list(df_sombreamentos['sombreamento']))))]

        # Cria um DataFrame temporário com os itens não sombreados do curso atual
        df_temp = pd.DataFrame({'tópico_formativo': itens_nao_sombreados,
                                'sombreamento': [[i] for i in itens_nao_sombreados],
                                'Cursos': [[row['Curso']] for i in itens_nao_sombreados],
                                'Códigos_de_Produto': [[row['Código_do_Produto']] for i in  itens_nao_sombreados]})

        # Concatena o DataFrame temporário ao DataFrame geral df_itens_nao_sombreados
        df_itens_nao_sombreados = pd.concat([df_itens_nao_sombreados, df_temp], ignore_index=True)


    # Imprimir o DataFrame com os itens não sombreados do primeiro curso
    # display(df_itens_nao_sombreados)

    pd.concat([df_sombreamentos, df_itens_nao_sombreados])



    # ====================================
    # ====================================
    #  Finalização

    df_TFs = pd.concat([df_itens_nao_sombreados, df_sombreamentos]).reset_index(drop=True)
    #display(df_TFs)


    #==========="DESSOMBREAMENTO" DE CONTEÚDO FORMATIVO ================================
    # ==================================================================================


    # Aqui vou cruzar as questões com o retorno do Forms

    inner_df = inner_join_by_str_match((df_quest_flag,'CAPACIDADE TÉCNICA Relacionada'), (df_TFs,'tópico_formativo'))

    #display(inner_df)



    # ==============================================PULP=======================================================
    # Resolvendo problema de Otimização (PL)
    # Encontrando cursos mínimos para ter contato com todos os Tópicos Formativos necessários


    # Criar um conjunto de todos os tópicos formativos desejados

    # # Se todos os tópicos desejados fossem os tópicos mais relevnates sombreados
    # todos_topicos_desejados = set(chain.from_iterable([s['sombreamento'] for s in mapeamento_sombreamentos]))

    # Se todos os tópicos desejados fossem os tópicos do FORMS
    todos_topicos_desejados = set(list(inner_df[inner_df['Pontuação']==0]['tópico_formativo']))


    # Criar um conjunto de todos os códigos de produtos únicos
    todos_codigos = set(list(CFs_cursos['Código_do_Produto']))


    # Crie um problema de PROGRAMAÇÂO LINEAR (PLI)
    prob = LpProblem("AlocacaoCursos", LpMinimize)

    # Variáveis binárias para representar se um curso é selecionado ou não
    x = LpVariable.dicts("CursoSelecionado", todos_codigos, 0, 1, LpBinary)

    # Função objetivo: minimizar o número de cursos selecionados
    prob += lpSum(x[codigo] for codigo in todos_codigos)

    # Restrição: cada tópico formativo desejado deve ser coberto
    for topico in todos_topicos_desejados:
        cursos_que_cobrem_topico = []
        for entry in inner_df.to_dict(orient='records'):
            if topico in entry['sombreamento']:
                cursos_que_cobrem_topico.extend(entry['Códigos_de_Produto'])
        prob += lpSum(x[codigo] for codigo in cursos_que_cobrem_topico) >= 1


    # Resolva o problema
    prob.solve()

    de_para_nomes_df = pd.merge(left=df_quest_flag, right=CFs_cursos, on='Código_do_Produto',how='inner')

    # Crie uma lista de cursos selecionados com suas informações
    cursos_selecionados = []
    for codigo in todos_codigos:
        if x[codigo].varValue == 1:
            curso_info = de_para_nomes_df[de_para_nomes_df['Código_do_Produto'] == codigo].iloc[0]
            curso = curso_info['Curso Relacionado']
            topicos_formativos = curso_info['Conteúdo_formativo']['CF_COMPLETO']
            cobre_topicos = sum(1 for topico in todos_topicos_desejados if topico in topicos_formativos)
            total_topicos = len(topicos_formativos)
            cobre_ratio = cobre_topicos / total_topicos
            total_desejados = len(todos_topicos_desejados)
            ratio_total_desejados = cobre_topicos / total_desejados

            cursos_selecionados.append({
                'Código de Produto': codigo,
                'Nome do Curso': curso,
                'Tópicos Formativos': len(topicos_formativos),
                'Razão Utilidade (Tópicos Desejados no Curso / Total de Tópicos no Curso)': cobre_ratio,
                'Razão Aderência (Tópicos Desejados no Curso / Total de Tópicos Desejados)': ratio_total_desejados
            })

    # Crie um DataFrame com os cursos selecionados
    df_resultados = pd.DataFrame(cursos_selecionados)

    # Ordene o DataFrame pelos cursos mais aderentes usando as razões de desejo
    df_resultados = df_resultados.sort_values(by='Razão Utilidade (Tópicos Desejados no Curso / Total de Tópicos no Curso)', ascending=False)

    # filtrando df
    df_resultados = df_resultados[df_resultados['Razão Aderência (Tópicos Desejados no Curso / Total de Tópicos Desejados)']>0]

    # Máscara dos resultados (%)
    df_resultados['Razão Utilidade (Tópicos Desejados no Curso / Total de Tópicos no Curso)'] = ["{:.2f}%".format(x*100) for x in df_resultados['Razão Utilidade (Tópicos Desejados no Curso / Total de Tópicos no Curso)']]
    df_resultados['Razão Aderência (Tópicos Desejados no Curso / Total de Tópicos Desejados)'] = ["{:.2f}%".format(x*100) for x in df_resultados['Razão Aderência (Tópicos Desejados no Curso / Total de Tópicos Desejados)']]

    
    if notebook!=0:
        # Imprima os resultados ordenados
        print("Resultados ordenados pelos cursos mais Úteis:")
        print(df_resultados)

    # ==============================================PULP=======================================================

    end = time.time()
    print("Recomendação finalizada em {:.2f}s".format(end-start))
    
    return base64str, df_resultados







# ====================================================
# ====================================================
# ====================================================
# ====================================================
# PROEDUCADOOOOOORRRR


def recommend_courses_auto(forms_data):
    
    # Essa é uma variável para quando se quer simula no jupyter notebook, marque 0 para prod
    notebook = 0

    start = time.time()

    #Leitura direto do Arquivo mastigado da Ingrid (Proeducador)

    xl = pd.read_excel(r"Matriz Assessment Pro Revisão Maria Carol Normalizada.xlsx")

    # Aqui vou definir as categorias de cada curso, para ajudar na fomração do Radar

    categorias = {c:list(dict.fromkeys([x['Capacidade'] for _,x in xl.iterrows() if x['Categoria']==c])) for c in list(dict.fromkeys(xl['Categoria']))}

    #print(categorias)


    # ============ FORMS ============================

    # LENDO DADOS DO FOMRS

    # Dados de entrada da API:

    d1 = forms_data['d1']
    d2 = forms_data['d2']

    # Manipulação e preparo

    d1 = d1.replace('false', 'False').replace('true', 'True')
    d2 = d2.replace('false', 'False').replace('true', 'True')


    d1 = ast.literal_eval(d1) # {Texto_Questão_Forms: ID_Questão_Forms ...}
    d2 = ast.literal_eval(d2) # {'responder': Email, 'submitDate':data_resposta}|{ID_Questão_Forms: Texto_Alternativa_selecionada}


    # "responder" : Email do docente
    # "submitDate" : Data de submissão do assessment
    # "rf2bab5b697ee4e519a2c7792da36b3e7": Profissão do responder
    # "re6b75c9e2f9c4f5a9a48dad1cda45b0a": Escola SENAI
    # "r828ff0126ed64ba78882fca6c38f7bc1": Turma da MSEP
    # "r2db339e80d284ab4ae0afc322489a860": Turmas que ele atende,
    # "r935fd5880ed4445ea8c5166c8ca76ac7": Data que fez curso da MSEP

    # Chaves a separar em d2
    track_q_ids= ["responder","submitDate","rf2bab5b697ee4e519a2c7792da36b3e7","re6b75c9e2f9c4f5a9a48dad1cda45b0a","r828ff0126ed64ba78882fca6c38f7bc1","r2db339e80d284ab4ae0afc322489a860","r935fd5880ed4445ea8c5166c8ca76ac7"]

    # Dados para o SQL assessment
    assessemment_tracking = {k:v for k,v in d2.items() if k in track_q_ids}

    
    # Parsing --------------------------------

    # Questões em d1 exceto a questão que pergunta o email 
    questions = {k:v for k,v in d1.items() if v not in track_q_ids}

    # Dicionaário D2 {ID_Questão: Texto_Alternativa_selecionada ...}
    user_answers = {k:v for k,v in d2.items() if k not in track_q_ids}

    # Criando o dicionário de {'ID_Questão_Forms': ponutuação}
    answers_scoring = {}

    scorecards = {'Ainda não consigo':0, 'Consigo com muita ajuda':1/3, 'Consigo com pouca ajuda':2/3, 'Sou capaz de ensinar':3/3}

    for k,v in user_answers.items():
        try:
            answers_scoring[k]= scorecards[v]
        except:
            answers_scoring[k]= 0


    # Criando um Dataframe Pandas

    forms_df = pd.DataFrame(columns=['ID_Questão_Forms','Texto_Questão_Forms','Texto_Alternativa_selecionada'])

    forms_df[['Texto_Questão_Forms','ID_Questão_Forms']] = list(questions.items())

    forms_df['Texto_Alternativa_selecionada'] = [user_answers[id_q] for id_q in forms_df['ID_Questão_Forms']]

    forms_df['Pontuação'] = [answers_scoring[id_q] for id_q in forms_df['ID_Questão_Forms']]


    # display(forms_df)


    # ---------------------------------------
    # Merge com os dados reais do FORMS no excel da Ingrid

    df_quest_pro = inner_join_by_str_match((xl,'Autoavaliação'), (forms_df,'Texto_Questão_Forms'))
    

    
    def radar_chart(dataframe, category_col, score_col):

        # Aggregating and summarizing by Categories and values for the Radar
        df = dataframe.groupby([category_col], as_index=False).agg({score_col:'mean'})
        
        """Create a radar chart of N categories, depending on how many rows the DataFrame has."""

        # Calculate the theta values
        theta = np.linspace(0, 2 * np.pi, len(df), endpoint=False)

        # Close the plot
        radii = df[score_col].tolist()
        radii += radii[:1]
        theta = np.append(theta, theta[0])

        # Create the radar chart
        fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': 'polar'})

        # Plot the edges of the area
        ax.fill(theta, radii, 'r', alpha=0.1)
        ax.plot(theta, radii, color='r', linewidth=2)

        # Place dots at the vertices
        ax.plot(theta[:-1], radii[:-1], 'ro', markersize=5)

        # Set the axis labels
        ax.set_xticks(theta[:-1])

        # Set the radar chart axis limits to ensure a fixed scale from 0 to 1
        ax.set_ylim(0, 1)

        # Customize the radius for the x-axis tick labels to move them further away
        radius_custom = -0.15  # Adjust this value for the desired distance
        ax.set_xticklabels(df[category_col], fontsize=12, va='center', position=(0, radius_custom))


        # Remove radial labels
        ax.set_yticklabels([])

        # Add data labels (values) on top of each radar point with an offset for readability
        for i, (x, y) in enumerate(zip(theta[:-1], radii[:-1])):
            offset = 0.15  # Adjust this value for the desired offset
            ax.text(x, y + offset, f'{y*100:.1f}%', fontsize=11, ha='center', va='bottom', color='r')


        # Set the title
        ax.set_title('Radar Assessment Proeducador', y=1.2)

        # Add a label indicating the scale in the bottom right corner outside the chart
        ax.text(1.3, -0.2, 'Scale: 0-100%', fontsize=12, ha='right', va='bottom', color='r', transform=ax.transAxes)


        return fig, ax


    # Create the radar chart
    fig, ax = radar_chart(df_quest_pro, category_col='Categoria', score_col='Pontuação')
    
    # dataframe
    asessment_results = df_quest_pro.groupby(['Categoria'], as_index=False).agg({'Pontuação':'mean'})
    
    if notebook!=0:
        # Show the chart
        plt.show()

        # Save the chart as a PNG file (not needed)
        plt.savefig('radar_chart.png', format='png')
    
    
    # Save the chart as a PNG file in memory (BytesIO)
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convert the image in memory to a base64 string
    base64str = base64.b64encode(buffer.read()).decode('utf-8')
    
    
    
    # =====================================================================
    # CRUD NA TABELA DO ASSESSMENT PRO

    # Configurações de conexão
    server = '10.163.39.25,1438'
    database = 'dbDataMasterGED'
    username = 'usdatamasterged'
    password = 'us@WIDToGgA8Nk55!R82M0'

    nome_tabela = 'BANCO_ASSESSMENT'


    #Redefifnindo a string de conexão
    # Para o docker, é necessário torcar o DRIVER de 'SQL Server' para 'ODBC Driver 17 for SQL Server', pois o docker roda Linux e o dockerfile instalou o driver 17 no ambiente
    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)

    # Criar um cursor para executar comandos SQL
    cursor = conn.cursor()

    injection_table_schema = [('responder', 'Email do docente'),
                               ('submitDate', '11/10/2023 1:53:17 PM'),
                               ('Cargo', 'Cargo do Docente'),
                               ('Unidade_Escolar_CFP', '105 : Escola SENAI - Barra Funda - Horácio Augusto da Silveira'),
                               ('Turma_MSEP', 'Tuma da MSEP qu articipou'),
                               ('Formacao_Academica', 'Formação do Docente'),
                               ('Data_de_inicio_do_curso', '11/10/2023'),
                               ('base64_img', "121111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111113"),
                               ('results', "[{'dado':121111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111113}]")]


    # # Registrando resultados no BANCO_ASSESSMENT

    # # Lista de tuplas com os dados para inserção no banco
    # injection_data = [
    #     ('abcdaenfs', 34567, 12.34, True, [1, 2, 3], {'dado': 123}),
    #     ('dadosdados', 6745, 750.99, False, [1, 2, 3, 4, 5], {'dado': 367}),
    # ]
    
    # Salvando o dataframe 'asessment_results' como JSON na coluna 'results'
    injection_data = tuple(list(assessemment_tracking.values()) + ['data:image/png;base64,'+str(base64str), asessment_results.to_json()])

    json.dumps(forms_data)
    
    #  Inserção dos valores dos hiperparâmetros na tabela
    insert_query = '''
    INSERT INTO {} ({})
    VALUES ({})
    '''.format(nome_tabela, ', '.join([k[0] for k in injection_table_schema]), '?, '*(len(injection_table_schema)-1)+'?')

    #print(insert_query)

    # Executando a adição de dados 
    cursor.execute(insert_query, injection_data)


    # Finaliza comitando
    conn.commit()


    if notebook!=0:
        # Exibição dos resultados:
        test = pd.read_sql('SELECT * FROM {}'.format(nome_tabela), conn)
        display(test)
    # =====================================================================


    end = time.time()
    print("Recomendação finalizada em {:.2f}s".format(end-start))
    
    return base64str






if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)