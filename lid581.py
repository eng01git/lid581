######################################################################################################
                                           #Introdução
######################################################################################################
# O sistema desenvolvido coleta os dados dos 5 porques através de um formulário web e armazena num  
# banco no-SQL. Esses dados são ligos e disponibilizados para visualização e edição

# Tecnologias:
# Streamlit para web, streamlit share para deploy, banco de dados Firebase (Google)

# Link:
# https://share.streamlit.io/eng01git/5pq/main/5pq.py
######################################################################################################
                                 # importar bibliotecas
######################################################################################################

import streamlit as st
from streamlit_tags import st_tags
from streamlit import caching
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import smtplib
from datetime import  date, datetime, time
import pytz
import base64
from io import BytesIO
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode, JsCode

from google.cloud import firestore
from google.oauth2 import service_account

######################################################################################################
				#Configurações da página
######################################################################################################

st.set_page_config(
     page_title="LID Forms",
     layout="wide",
)

######################################################################################################
				#Configurando acesso ao firebase
######################################################################################################

# Pega as configurações do banco do segredo
key_dict = json.loads(st.secrets["textkey_2"])
creds = service_account.Credentials.from_service_account_info(key_dict)

# Seleciona o projeto
db = firestore.Client(credentials=creds, project="lid-forms")

######################################################################################################
				     #Definição da sidebar
######################################################################################################

fig1s, fig2s, fig3s = st.sidebar.beta_columns([1,2,1])
fig1s.write('')
fig2s.image('latas minas.png', width=150)
fig3s.write('')
st.sidebar.title("LID Forms")
tipos = ['CIL', 'Troubleshoot']
selecao_tipo = st.sidebar.radio('Selecione o tipo do formulario', tipos)

tz = pytz.timezone('America/Bahia')

formularios_cil = [
	'Liner diário',
	'Liner semanal',
	'Shell diário',
	'Shell semanal',
	'Autobagger diário',
	'Autobagger semanal',
	'Autobagger mensal',
	'Conversion diário',
	'Conversion semanal',
	'Conversion mensal',
	'Balancer diário',
	'Balancer semanal',
	'Estatisticas',			# Gráficos com filtros
	'Visualizar formulários',	# Filtros para visualizar os questionários desejeados
	'Suporte Engenharia'
]
formularios_cil_2 = ['Liner diário','Liner semanal','Shell diário','Shell semanal','Autobagger diário','Autobagger semanal','Autobagger mensal',
		     'Conversion diário','Conversion semanal','Conversion mensal','Balancer diário','Balancer semanal']

formularios_trouble = [
	'Liner',
	'Shell Press',
	'Autobagger',
	'Conversion Press',
	'Balancer A',
	'Balancer B',
	'GFS',
	'Dry Oven',
	'Tab Uncoiler',
	'Estatisticas',			# Gráficos com filtros
	'Visualizar Troubleshoot',	# Filtros para visualizar os questionários desejeados
	'Suporte Engenharia']

if selecao_tipo == 'CIL':
	func_escolhida = st.sidebar.radio('Selecione o formulário CIL', formularios_cil, index=0)
	
if selecao_tipo == 'Troubleshoot':
	func_escolhida = st.sidebar.radio('Selecione o formulário de Troubleshoot', formularios_trouble, index=0)

######################################################################################################
                               #Função para gerar planilha interativa
######################################################################################################	
	
def config_grid(df, definition):
	sample_size = 12
	grid_height = 400

	return_mode = 'AS_INPUT'
	return_mode_value = DataReturnMode.__members__[return_mode]

	update_mode = 'MODEL_CHANGED'
	update_mode_value = GridUpdateMode.__members__[update_mode]

	#enterprise modules
	enable_enterprise_modules = False
	enable_sidebar = False

	#features
	fit_columns_on_grid_load = False
	enable_pagination = False
	paginationAutoSize = False
	use_checkbox = True
	enable_selection = False
	selection_mode = 'multiple'
	rowMultiSelectWithClick = False
	suppressRowDeselection = False

	if use_checkbox:
		groupSelectsChildren = True
		groupSelectsFiltered = True

	#Infer basic colDefs from dataframe types
	gb = GridOptionsBuilder.from_dataframe(df)

	#customize gridOptions
	gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)

	if enable_selection:
		gb.configure_selection(selection_mode)
	if use_checkbox:
		gb.configure_selection(selection_mode, use_checkbox=True, groupSelectsChildren=groupSelectsChildren, groupSelectsFiltered=groupSelectsFiltered)
	if ((selection_mode == 'multiple') & (not use_checkbox)):
		gb.configure_selection(selection_mode, use_checkbox=False, rowMultiSelectWithClick=rowMultiSelectWithClick, suppressRowDeselection=suppressRowDeselection)

	if enable_pagination:
		if paginationAutoSize:
			gb.configure_pagination(paginationAutoPageSize=True)
		else:
			gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=paginationPageSize)

	gb.configure_grid_options(domLayout='normal')
	gridOptions = gb.build()
	return gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules

######################################################################################################
                               #Função para leitura do banco (Firebase)
######################################################################################################
# Efetua a leitura de todos os documentos presentes no banco e passa para um dataframe pandas
# Função para carregar os dados do firebase (utiliza cache para agilizar a aplicação)

# Formularios cil
@st.cache
def load_forms_cil(col):

	# Cria dicionário vazio
	dicionario = {}
	
	# Define o caminho da coleção do firebase
	posts_ref = db.collection(col)
	
	index = 0
	# Busca todos os documentos presentes na coleção e salva num dicionário
	for doc in posts_ref.stream():
		dic_auxiliar = doc.to_dict()
		dicionario[str(index)] = dic_auxiliar
		index += 1
	
	# Ajusta o dicionário para um dataframe
	forms_df = pd.DataFrame.from_dict(dicionario)
	forms_df = forms_df.T
	forms_df.reset_index(inplace=True)
	forms_df.drop('index', axis=1, inplace=True)
	
	# Formata as colunas de data e hora para possibilitar filtros
	forms_df['I2'] = pd.to_datetime(forms_df['I2'])
	 	
	# Ordena os valores pela data
	forms_df.sort_values(by=['I2'], inplace=True)
	return forms_df

# Formularios troubleshoot
@st.cache
def load_forms(colecao):
	# Cria dicionário vazio
	dicionario = {}
	
	# Define o caminho da coleção do firebase
	posts_ref = db.collection(colecao)
	
	index = 0
	# Busca todos os documentos presentes na coleção e salva num dicionário
	for doc in posts_ref.stream():
		dic_auxiliar = doc.to_dict()
		dicionario[str(index)] = dic_auxiliar
		index += 1
	
	# Ajusta o dicionário para um dataframe
	forms_df = pd.DataFrame.from_dict(dicionario)
	forms_df = forms_df.T
	forms_df.reset_index(inplace=True)
	forms_df.drop('index', axis=1, inplace=True)
	
	# Lista e ordena as colunas do dataframe
	lista_colunas = ['Equipamento', 'Data', 'Nome', 'Turno', 'Nv1', 'Nv2', 'Causa', 'Solucao', 'Resolveu', 'Comentario']
	forms_df = forms_df.reindex(columns=lista_colunas)
	
	# Formata as colunas de data e hora para possibilitar filtros
	forms_df['Data'] = pd.to_datetime(forms_df['Data']).dt.date
	
	# Ordena os valores pela data
	forms_df.sort_values(by=['Data'], inplace=True)
	return forms_df

# FUncionarios LIDS
@st.cache
def load_users():
	users = pd.read_csv("LIDS_nomes.csv")
	return users

@st.cache
def load_data():
	data = pd.read_csv(DATA_URL)
	
	# Define o caminho da coleção do firebase
	posts_ref = db.collection("5porques_2")	
	
	# Busca todos os documentos presentes na coleção e salva num dataframe
	for doc in posts_ref.stream():
		dicionario = doc.to_dict()
		dicionario['document'] = doc.id
		data = data.append(dicionario, ignore_index=True)
	
	# Formata as colunas de data e hora para possibilitar filtros
	data['data'] = pd.to_datetime(data['data']).dt.date
	data['hora'] = pd.to_datetime(data['hora']).dt.time
	return data

# Efetua a leitura dos dados dos usuários no banco
@st.cache
def load_usuarios():
	# Define as colunas do dataframe
	data_user = pd.DataFrame(columns=['Nome', 'Email', 'Gestor', 'Codigo'])
	
	# Define o caminho da coleção do firebase
	posts_ref = db.collection("Users")	
	
	# Busca todos os documentos presentes na coleção e salva num dataframe
	for doc in posts_ref.stream():
		dicionario = doc.to_dict()
		dicionario['document'] = doc.id
		data_user = data_user.append(dicionario, ignore_index=True)
	return data_user

# Efetua a escrita das ações no banco de dados
def write_acoes(acoes, documento, gestor):
	
	# Define o caminho da coleção do firebase
	posts_ref = db.collection("acoes")	
	
	# Lista e dicionario vazio
	acoes_firebase = []
	dic_to_firebase = {}
	
	# Busca todos os documentos presentes na coleção e salva num dataframe
	for doc in posts_ref.stream():
		acoes_firebase.append(doc.id)
		
	index = 0
	
	# Itera sobre todas as ações do 5-Porques
	for i in acoes:
		
		# Separa a string
		lista = i.split(";;")
		
		# Define o nome do documento a ser armazenado na base de dados
		chave = str(documento) + '_' + str(index)
		
		# Verifica se a ação já consta no banco de dados
		if chave not in acoes_firebase:	
			
			# Definição da ação com alteração do status para em aberto
			dic_to_firebase[chave] = {'Ação': lista[0],
						  'Dono': lista[1],
						  'Prazo': lista[2],
						  'Numero da ação': index,
						  'Numero do 5-Porques': documento,
						  'Status': 'Em aberto',
						  'Gestor': gestor,
						  'E-mail': 'Não enviado',
						  'Editor': '',
						  'Data': ''
						 }		
			db.collection("acoes").document(chave).set(dic_to_firebase[chave],merge=True)
			
			# Envia email para o dono da acao 
			remetente = usuarios_fb.loc[usuarios_fb['Nome'] == lista[1], 'Email'].to_list()
			send_email(remetente[0], 6, lista[2], lista[0], 0)
			time.sleep(1)
			#send_email(to, atividade, documento, comentario, gatilho):
			
		else:
			
			# Caso a ação já esteja no banco de dados, ela é modificada mas seu status não é alterado
			dic_to_firebase[chave] = {'Ação': lista[0],
						  'Dono': lista[1],
						  'Prazo': lista[2],
						  'Numero da ação': index,
						  'Numero do 5-Porques': documento,
						  'Gestor': gestor,
						  'E-mail': 'Não enviado'
						 }		
			db.collection("acoes").document(chave).set(dic_to_firebase[chave],merge=True)
		index += 1

# Grava a edição das ações no banco
def gravar_acao_edit(row):
	ea_chave = str(row['Numero do 5-Porques']) + '_' + str(row['Numero da ação'])
	row_string = row.astype(str)
	db.collection("acoes").document(ea_chave).set(row_string.to_dict(),merge=True)
	caching.clear_cache()

######################################################################################################
                                           #Função para enviar email
######################################################################################################
# Recebe como parâmetros destinatário e um código de atividade para o envio
# O email está configurado por parâmetros presentes no streamlit share (secrets)
def send_email(to, atividade, documento, comentario, gatilho):
	
	# Configura quem vai enviar o email
	gmail_user = st.secrets["email"]
	gmail_password = st.secrets["senha"]
	sent_from = gmail_user
	
	# Cria os campos que estarão no e-mail
	from_ = 'LID Forms'
	subject = ""
	body = ''
	atividade = int(atividade)
	
	# Verifica o código da atividade e edita a mensagem (criação, retificação, aprovação ou reproavação de 5-Porques
	# Criação
	if atividade == 0:
		body = "Olá, foi gerada um novo 5-Porques, acesse a plataforma para avaliar.\nhttps://share.streamlit.io/eng01git/5pq/main/5pq.py\n\nAtenciosamente, \nAmbev 5-Porques"
		subject = """Gerado 5-Porques %s""" % (documento)
	
	# Mensagem pro suporte
	elif atividade == 4:
		body = """Olá, segue mensagem enviada ao suporte.\n\n%s \n\nAtenciosamente, \nAmbev 5-Porques""" %(comentario)
		subject = 'Suporte LID Forms'
	
	# Transforma o remetente em lista
	list_to = [to]
	
	# Verifica se precisa mandar o e-mail para a engenharia
	if int(gatilho) > 60:	
		pass
	
	# Monta a mensagem
	email_text = """From: %s\nTo: %s\nSubject: %s\n\n%s
	""" % (from_, list_to, subject, body)
	
	# Envia a mensagem
	try:
		server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
		server.ehlo()
		server.login(gmail_user, gmail_password)
		server.sendmail(sent_from, list_to, email_text.encode('latin-1'))
		server.close()
		st.write('E-mail enviado!')
	except:
		st.error(list_to)

######################################################################################################
                                           #Função para download
######################################################################################################
# download de csv		
def download(df):
	"""Generates a link allowing the data in a given panda dataframe to be downloaded
	in:  dataframe
	out: href string
	"""
	csv = df.to_csv(index=False)
	b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
	href = f'<a href="data:file/csv;base64,{b64}">Download dos dados como csv</a>'
	return href

# Gera arquivo excel
def to_excel(df):
	output = BytesIO()
	writer = pd.ExcelWriter(output, engine='xlsxwriter')
	df.to_excel(writer, sheet_name='Sheet1')
	writer.save()
	processed_data = output.getvalue()
	return processed_data

# Gera o link para o download do excel
def get_table_download_link(df):
	"""Generates a link allowing the data in a given panda dataframe to be downloaded
	in:  dataframe
	out: href string
	"""
	val = to_excel(df)
	b64 = base64.b64encode(val)  # val looks like b'...'
	return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="dados.xlsx">Download dos dados em Excel</a>' # decode b'abc' => abc

			   
######################################################################################################
                              #Formulários
######################################################################################################

def Liner_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes) 
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Retirar a escova do suporte, depositar a escova dentro do recipiente com solução de limpeza durante 30 minutos.  Inspecionar as escovas para detectar possíveis anomalias e desgastes.')
		T01.info('Limpeza das guias de saída: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar as saídas para detectar possíveis anomalias e desgastes.')
		T02.info('Limpeza do conjunto Lower Turret e Upper Turret: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar o conjunto para detectar possíveis anomalias e desgastes.')
		T03.info('Limpeza da mesa e da Star Wheel: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar a mesa para detectar possíveis anomalias e desgastes.')
		T04.info('Limpeza ao redor do piso do equipamento: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
		T05.info('Limpeza Balancer "B": 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
		T06.info('Limpeza do visor da estação de aplicação de vedante: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
		T07.info('Limpeza nos furos do Hopper: 1-Limpeza utilizando pano umedecido com álcool isopropílico.')
		T08.info('Limpeza na calha de rejeito das  correias transportadoras: 1-Limpeza utilizando pano umedecido com álcool isopropílico.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("Liner_diario").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

def Liner_diario_proc():
	with st.beta_expander('Pontos'):
		st.image('liner_diario/Pontos diaria liner.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('liner_diario/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('liner_diario/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('liner_diario/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('liner_diario/folha4.jpg')
				
	with st.beta_expander('Procedimentos folha 5'):
		st.image('liner_diario/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('liner_diario/folha6.jpg')
		
def Liner_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		T09, Q09, C09 = st.beta_columns([3,1,3])
		T10, Q10, C10 = st.beta_columns([3,1,3])
		T11, Q11, C11 = st.beta_columns([3,1,3])
		T12, Q12, C12 = st.beta_columns([3,1,3])
		T13, Q13, C13 = st.beta_columns([3,1,3])
		T14, Q14, C14 = st.beta_columns([3,1,3])
		T15, Q15, C15 = st.beta_columns([3,1,3])
		T16, Q16, C16 = st.beta_columns([3,1,3])
		T17, Q17, C17 = st.beta_columns([3,1,3])
		T18, Q18, C18 = st.beta_columns([3,1,3])
		T19, Q19, C19 = st.beta_columns([3,1,3])
		T20, Q20, C20 = st.beta_columns([3,1,3])
		T21, Q21, C21 = st.beta_columns([3,1,3])
		T22, Q22, C22 = st.beta_columns([3,1,3])
		T23, Q23, C23 = st.beta_columns([3,1,3])
		T24, Q24, C24 = st.beta_columns([3,1,3])
		T25, Q25, C25 = st.beta_columns([3,1,3])
		T26, Q26, C26 = st.beta_columns([3,1,3])
		T27, Q27, C27 = st.beta_columns([3,1,3])
		T28, Q28, C28 = st.beta_columns([3,1,3])
		T29, Q29, C29 = st.beta_columns([3,1,3])
		T30, Q30, C30 = st.beta_columns([3,1,3])
		T31, Q31, C31 = st.beta_columns([3,1,3])
		T32, Q32, C32 = st.beta_columns([3,1,3])
		T33, Q33, C33 = st.beta_columns([3,1,3])
				
		# Texto das questões
		T00.info('Limpeza Conveyor #1 BALN e Pushers 1,2,3,4: 1- Limpar com pano umedecido  e álcool isopropílico.')
		T01.info('Limpeza Conveyor #2 BA-LN e Pushers 1,2,3,4: 1- Limpar com pano umedecido  e álcool isopropílico.')
		T02.info('Limpeza Conveyor #3 BA-LN e Pushers 1,2,3,4,5: 1- Limpar com pano umedecido  e álcool isopropílico.')
		T03.info('Limpeza Conveyor #4 BA-LN e Pushers 1,2,3,4,5: 1- Limpar com pano umedecido  e álcool isopropílico.')
		T04.info('Limpeza Conveyor #4 BA-LN e Pushers 1,2,3,4,5,6: 1- Limpar com pano umedecido  e álcool isopropílico.')
		T05.info('Limpeza da esteira de alimentação:  1-Limpar a superfície utilizando pano umedecido com álcool isopropílico. Inspecionar a esteira para detectar possíveis anomalias e desgastes.')
		T06.info('Desmontagem e limpeza do Downstacker: 1- Limpar o seu interior com o auxílio de um aspirador pneumático, após limpe com um pano umedecido  em álcool isopropílico toda a área aspirada. Inspecionar o equipamento para detectar possíveis anomalias e desgastes.')
		T07.info('Limpeza da mesa e da Star Wheel: 1- Limpar com pano umedecido em álcool isopropílico toda a superfície da mesa do Lower Turret que ainda não foi limpa, se necessário utilize a haste metálica pontiaguda para retirar compound preso nas juntas ou fissuras  Limpe toda a face da Star Wheel. Limpe as portas/gaiolas de proteção do lado externo e interno.')
		T08.info('Limpeza da caixa de óleo: 1- Limpar com pano umedecido em álcool isopropílico as laterais do lado de dentro da caixa de gotejamento de óleo. Não é necessário fazer sangria ou limpar o fundo/parte de baixo da caixa.')
		T09.info('Limpeza da correia transportadora de saída do Liner: 1-Limpar com pano umedecido em álcool isopropílico.')
		T10.info('Limpeza das guias de descargas: 1-Limpar com pano umedecido em álcool isopropílico.')
		T11.info('Limpeza da Plate Turrent Suport, Seal Retainer e Lower Chuck: 1-Limpar com pano umedecido em álcool isopropílico.')
		T12.info('Limpeza dos Hopper: 1-Limpar com pano umedecido em álcool isopropílico.')
		T13.info('Limpeza na estrutura dos fornos e pisos: 1-Limpar com pano umedecido em álcool isopropílico.')
		T14.info('Limpeza nas estruturas da máquina: 1-Limpar com pano umedecido em álcool isopropílico.')
		T15.info('Limpeza nos pushers do mezanino e nos pushers após o Hopper na parte de baixo proximo ao piso: 1-Limpar com pano umedecido em álcool isopropílico.')
		T16.info('Limpeza da guarda pelo lado interno: 1-Limpar com pano umedecido em álcool isopropílico.')
		T17.info('Limpeza da Conveyor #1 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
		T18.info('Limpeza da Conveyor #2 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
		T19.info('Limpeza da Conveyor #3 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
		T20.info('Limpeza da Conveyor #4 LN-BB e Pushers 1,2,3 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
		T21.info('Limpeza da Conveyor #5 LN-BB e Pushers 1,2,3 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
		T22.info('Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar água e pistola de ar.')
		T23.info('Daytank - Limpeza dos filtros de alimentação da linha: 1- Utilizar água e pistola de ar.')
		T24.info('Verificar visualmente todo sistema, para ver se não á anomalias.')
		T25.info('Verificar a quantidade de selante, abastecer se necessário.')
		T26.info('Limpar do filtro "Y" da mangueira de sucção ou antes de inciar o abastecimento de um novo IBC. 1-Utilizar água e pistola de ar.')
		T27.info('Verificar a pressão de ar comprimido na unidade de consevarção.')
		T28.info('Verificar a pressão do sitema de alimentação do selante.')
		T29.info('Limpar o filtro do selante caso tenha sido substituido no item 11, ou descartar se estiver danificado. 1-Utilizar água e pistola de ar.')
		T30.info('Inspecionar conjunto do agitador em cima do reservatório de selante.')
		T31.info('Realizar 5S geral da área.')
		T32.info('Limpar externamente o tank. 1-Limpar com pano umedecido e álcool isopropílico.')
		T33.info('Daytank: Limepeza do filtro de selante na alimentação do Tanque: 1-Utilizar água e pistola de ar.')
				
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.radio('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.radio('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.radio('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.radio('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.radio('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.radio('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.radio('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.radio('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.radio('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.radio('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		dic['Q19'] = Q19.radio('Item 19:', respostas)
		dic['C19'] = C19.text_input('Comentário item 19:', "")
		dic['Q20'] = Q20.radio('Item 20:', respostas)
		dic['C20'] = C20.text_input('Comentário item 20:', "")
		dic['Q21'] = Q21.radio('Item 21:', respostas)
		dic['C21'] = C21.text_input('Comentário item 21:', "")
		dic['Q22'] = Q22.radio('Item 22:', respostas)
		dic['C22'] = C22.text_input('Comentário item 22:', "")
		dic['Q23'] = Q23.radio('Item 23:', respostas)
		dic['C23'] = C23.text_input('Comentário item 23:', "")
		dic['Q24'] = Q24.radio('Item 24:', respostas)
		dic['C24'] = C24.text_input('Comentário item 24:', "")
		dic['Q25'] = Q25.radio('Item 25:', respostas)
		dic['C25'] = C25.text_input('Comentário item 25:', "")
		dic['Q26'] = Q26.radio('Item 26:', respostas)
		dic['C26'] = C26.text_input('Comentário item 26:', "")		
		dic['Q27'] = Q27.radio('Item 27:', respostas)
		dic['C27'] = C27.text_input('Comentário item 27:', "")
		dic['Q28'] = Q28.radio('Item 28:', respostas)
		dic['C28'] = C28.text_input('Comentário item 28:', "")		
		dic['Q29'] = Q29.radio('Item 29:', respostas)
		dic['C29'] = C29.text_input('Comentário item 29:', "")
		dic['Q30'] = Q30.radio('Item 30:', respostas)
		dic['C30'] = C30.text_input('Comentário item 30:', "")
		dic['Q31'] = Q31.radio('Item 31:', respostas)
		dic['C31'] = C31.text_input('Comentário item 31:', "")
		dic['Q32'] = Q32.radio('Item 32:', respostas)
		dic['C32'] = C32.text_input('Comentário item 32:', "")
		dic['Q33'] = Q33.radio('Item 33:', respostas)
		dic['C33'] = C33.text_input('Comentário item 33:', "")
			 
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("Liner_semanal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Liner_semanal_proc():
	with st.beta_expander('Pontos'):
		st.image('liner_semanal/Pontos semanal liner.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('liner_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('liner_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('liner_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('liner_semanal/folha4.jpg')
				
	with st.beta_expander('Procedimentos folha 5'):
		st.image('liner_semanal/folha5.jpg')				

def Shell_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		T09, Q09, C09 = st.beta_columns([3,1,3])
		T10, Q10, C10 = st.beta_columns([3,1,3])
		T11, Q11, C11 = st.beta_columns([3,1,3])
		T12, Q12, C12 = st.beta_columns([3,1,3])
		T13, Q13, C13 = st.beta_columns([3,1,3])
		T14, Q14, C14 = st.beta_columns([3,1,3])
		T15, Q15, C15 = st.beta_columns([3,1,3])
		T16, Q16, C16 = st.beta_columns([3,1,3])
		T17, Q17, C17 = st.beta_columns([3,1,3])
		T18, Q18, C18 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Limpeza Sistema de curlers e sincronizers: 1- Limpeza com uma flanela umedecida em álcool isopropílico das mesas quatro mesas de curlers  e sincronizers removendo o pó de alumínio acumulado sobre os mesmos.')
		T01.info('Limpeza da parte interna do ferramental: 1- Limpar com uma flanela umedecida em álcool isopropílico todo o perímetro do ferramental, removendo pó de alumínio e pequenas farpas que possam danificar as shells durante a produção. 2-Com uma flanela limpa umedecida em álcool isopropílico, limpar toda a região das hastes dos cilindros da guardas de proteção após a limpeza soprar com o ar comprimido para secar. 3-Inspecionar o upper die verificando a existência de vazamento nos sistemas hidráulico e pneumático. Obs: Executar a limpeza a cada troca de bobina e observar o esqueleto da chapa para identificar possíveis rebarbas no produto.')
		T02.info('Limpeza dos blowers: 1. Com um flanela umedecida em álcool isopropílico limpar todas as saídas removendo toda sujidade.')
		T03.info('CILindro do quick lifit: 1. Verificar quanto a vazamentos de óleo.')
		T04.info('Unidade de ajuste de pressão (stand de ar): 1. Utilizando tato e audição verificar quanto a vazamentos.')
		T05.info('Gaiola de esferas das colunas: 1-Verificar a eficiência da lubrificação do conjunto de guias, observando se há uma película fina de oleo e ausência de vazamentos.')
		T06.info('Limpar o piso: 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
		T07.info('Limpar área ao redor da prensa: 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
		T08.info('Limpeza do painel de controle e bancadas: 1-Limpa com pano seco.')
		T09.info('Limpeza no Balancer "A": 1- Limpeza com uma flanela umedecida em álcool isopropílico.')
		T10.info('Limpeza da estrutura da máquina. (Acrílicos, Guarda Corpos, Proteções): 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
		T11.info('Limpeza nas partes acessíveis da prensa: 1- Limpar com uma flanela umedecida em álcool isopropílico todo o perímetro do ferramental, removendo pó de alumínio e pequenas farpas que possam danificar as shells durante a produção. Bloquei ode energia SAM/LOTOTO. Realizar o bloqueio de energia e verificar a eficácia do mesmo.')
		T12.info('Preparação: Separar e conferir todas as ferramentas, materiais e produtos indicados no item nº 2 do procedimento.')
		T13.info('Inspeção e limpeza do GFS: Utilizando um pano umedecido com álcool isopropílico, limpe os rolos do acumulador de loop. Após a limpeza, utilizando o tato, passe a mão em torno dos rolos a fim de detectar possíveis ondulações e pequenas protuberâncias nos rolos. Observar também a existência de componentes necessitando de reaperto.')
		T14.info('Inspeção e limpeza do rolo de alimentação de lâmina: Utilizando um pano umedecido com álcool isopropílico, limpe os rolos do acumulador de loop. Após a limpeza, utilizando o tato, passe a mão em torno dos rolos a fim de detectar possíveis ondulações e pequenas protuberâncias nos rolos. Observar também a existência de componentes necessitando de reaperto.')
		T15.info('Curler: Bloqueio de energia. Execute o bloquei ode energia conforme o procedimento e em seguida verifique a eficácia do mesmo.')
		T16.info('Preparação: Preparar os materiais para a limpeza e inspeção.')
		T17.info('Limpeza dos segmentos do Curler: Utilizando uma haste de latão, retire todas as tampas presas nos segmentos do Curler (se houver). Em seguida, aplique ar comprimido e limpe todos os segmentos com um pano umedecido em álcool isopropílico.')
		T18.info('Limpeza externa: "Utilizando um pano umedecido em álcool isopropílico, limpe toda a parte externa do Curler como mesa, estrutura externa (com exceção das tampas de acrílico) a fim de remover toda a poeira presente. Para limpar as tampas de acrílico, utilize um pano seco e limpo a fim de remover toda a sujidade existente."')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.radio('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.radio('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.radio('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.radio('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.radio('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.radio('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.radio('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.radio('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.radio('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.radio('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("shell_diario").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Shell_diario_proc():
	with st.beta_expander('Pontos'):
		st.image('shell_diario/Pontos diario shell.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('shell_diario/Procedimento de limpeza curler_folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('shell_diario/Procedimento de limpeza curler_folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('shell_diario/Procedimento de limpeza curler_folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria gfs_folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 5'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria gfs_folha2.jpg')
		
	with st.beta_expander('Procedimentos folha 6'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria gfs_folha3.jpg')
		
	with st.beta_expander('Procedimentos folha 7'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria gfs_folha3.jpg')
		
	with st.beta_expander('Procedimentos folha 8'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria gfs_folha4.jpg')
		
	with st.beta_expander('Procedimentos folha 9'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria shell_folha1.jpg')
	
	with st.beta_expander('Procedimentos folha 10'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria shell_folha2.jpg')
		
	with st.beta_expander('Procedimentos folha 11'):
		st.image('shell_diario/Procedimento de limpeza e inspeção diaria shell_folha3.jpg')
		
def Shell_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		T09, Q09, C09 = st.beta_columns([3,1,3])
		T10, Q10, C10 = st.beta_columns([3,1,3])
		T11, Q11, C11 = st.beta_columns([3,1,3])
		T12, Q12, C12 = st.beta_columns([3,1,3])
		T13, Q13, C13 = st.beta_columns([3,1,3])
		T14, Q14, C14 = st.beta_columns([3,1,3])
		T15, Q15, C15 = st.beta_columns([3,1,3])
		T16, Q16, C16 = st.beta_columns([3,1,3])
		T17, Q17, C17 = st.beta_columns([3,1,3])
		T18, Q18, C18 = st.beta_columns([3,1,3])
		T19, Q19, C19 = st.beta_columns([3,1,3])
		T20, Q20, C20 = st.beta_columns([3,1,3])

		
		# Texto das questões
		T00.info('Saída de shells para as curlers: 1-Limpar o sistema transporte das shells fazendo movimentos alternados de vai e vem nas 24 saídas de forma a retirar toda sujeira do percurso.')
		T01.info('Sistema de scrap: 1-Limpar o sistema de scrap verificando sempre se não há nenhum resto de chapa ou shell presa no percurso do sistema.')
		T02.info('Die set: 1-Remover as striper plate e stock plate; 2-Limpar todo perímetro do lower die e upper die ;3- Limpar a stipper plate e montar as mesmas no lower die; 4- Limpar a stock plate  e montar no upper die.')
		T03.info('Sistema de vácuo: 1-Limpeza e inspeção das válvulas.')
		T04.info('Pushers: 1-Descarregar os pushers e com uma flanela umedecida com álcool isopropílico limpar e inspecionar toda a parte interna e externa dos mesmos .')
		T05.info('Air eject: 1-Checar visualmente as condições do componente, e utilizando o tato e audição para identificar possíveis vazamentos.')
		T06.info('Limpeza na estrutura da máquina (bases, mangueiras, laterais, acrílicos, bancadas e piso): 1- Limpeza com pano umedecido e álcool isopropílico')
		T07.info('Limpeza com ar nos segmentos do Curler: 1- Utilizar a pistola de ar.')
		T08.info('Limpeza nas áreas dos Curlers (curlers, mesas, plataformas e tampas caídas): 1-Limpeza com pano umedecido em álcool isopropílico .')
		T09.info('Limpeza dos synchronizers (limpar guardas, tampas caídas, hopper, armor start´s e passar escovas no Screws): 1- Limpeza com pano umedecido em álcool isopropílico .')
		T10.info('Limpar Conveyor #1 SP-BA e Pushers 1,2,3,4 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T11.info('Limpar Conveyor #2 SP-BA e Pushers 1,2,3,4 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T12.info('Limpeza Conveyor #3 SP-BA e Pushers 1,2,3,4,5 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T13.info('Limpeza Conveyor #4 SP-BA e Pushers 1,2,3,4,5 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T14.info('Limpeza Conveyor #5 SP-BA e Pushers 1,2,3 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T15.info('Limpeza Conveyor #6 SP-BA e Pushers 1,2,3 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T16.info('Limpeza Conveyor #7 SP-BA e Pushers 1,2 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T17.info('Limpeza Conveyor #8 SP-BA e Pushers 1,2 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
		T18.info('GFS Bloqueio de energia: Execute o bloqueio de energia conforme o padrão e testar a eficácia do mesmo. Preparar os materiais conforme a necessidade.')
		T19.info('Limpeza parte externa da máquina: Limpar parte externa do equipamento utilizando pano umedecido com álcool isopropílico.')
		T20.info('Unidade de conservação de Ar: Drenar a água do filtro da linha pneumática.')

			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.radio('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.radio('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.radio('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.radio('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.radio('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.radio('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.radio('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.radio('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.radio('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.radio('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		dic['Q19'] = Q19.radio('Item 19:', respostas)
		dic['C19'] = C19.text_input('Comentário item 19:', "")
		dic['Q20'] = Q20.radio('Item 20:', respostas)
		dic['C20'] = C20.text_input('Comentário item 20:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("shell_semanal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Shell_semanal_proc():
	with st.beta_expander('Pontos'):
		st.image('shell_semanal/Pontos shell semanal.jfif')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('shell_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('shell_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('shell_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('shell_semanal/folha4.jpg')
		

def Autobagger_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Recolhimento de tampas (Autobagger Área do piso no entorno do equipamento, é área do piso interior do equipamento.): 1- Limpeza utilizando uma vassoura, pá e soprador de ar. Com as mãos, retire as tampas que ficaram presas dentro dos trays do Auto Bagger. Utilize o soprador para retirar as tampas do chão em parte de difícil acesso e logo após deve-se varrer e recolher as tampas utilizando a pá, e colocar no balde de scrap.')
		T01.info('Proteções e parte externa das máquinas (Área do pallettizer / autobagger): 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe alguma anomalia.')
		T02.info('Limpeza dos filtros (entrada e saída) - Autobagger e Palettizer Unidade de conservação (verificar a numeração em campo): 1- Limpeza de ambos os filtros (filtro de partículas e filtro coalescente) utilizando fluxo de ar e drenagem. Deve-se observar se os mesmos estão saturados, se caso estiver, devem ser trocados..')
		T03.info('Temperatura do aquecedor (Autobagger Sistema de fechamento do Bag): 1- Realizar o check diário da correta especificação de temperatura.')
		T04.info('Limpeza de todas as portas da área do Autobagger. 1- Limpar com pano  umedecido e álcool isopropílico.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("autobagger_diario").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Autobagger_diario_proc():
	with st.beta_expander('Pontos'):
		st.image('autobagger_diario/pontos diario autobagger.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('autobagger_diario/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('autobagger_diario/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('autobagger_diario/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('autobagger_diario/folha4.jpg')
		
	with st.beta_expander('Procedimentos folha 5'):
		st.image('autobagger_diario/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('autobagger_diario/folha6.jpg')

def Autobagger_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Limpeza dos trilhos de transporte das tampas: 1- Limpar os trilhos com pano seco, após a limpeza observar se existem partes soltas ou com folga.')
		T01.info('Limpar o braço do robô: 1- Limpeza com pano umedecido em álcool isopropílico, nas articulações e espelhos dos sensores. Inspecionar toda a área se existe  alguma anomalia.')
		T02.info('Limpeza do painel de operação IHM: 1- Limpar com um pano seco toda a interface da IHM')
		T03.info('Limpeza do sistema de armazenamento / transferência de tampas nas trays: 1- Executar limpeza do excesso de graxa dos rolamentos, mancais, limpeza dos rolos e correntes de transmissão. Limpar mesa de transferência e unidade de conservação.')
		T04.info('Finalizar a limpeza e colocar a máquina em operação: 1- Após o procedimento de limpeza conferir se não há componentes esquecidos dentro da máquina. Deve-se garantir que não haja ninguém dentro do perímetro de proteção da máquina. Seguir todo o procedimento de partida após intervenção na máquina.')
		T05.info('Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar pistola de ar.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("autobagger_semanal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Autobagger_semanal_proc():
	with st.beta_expander('Pontos'):
		st.image('autobagger_semanal/pontos semanal autobagger.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('autobagger_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('autobagger_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('autobagger_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('autobagger_semanal/folha4.jpg')
		
	with st.beta_expander('Procedimentos folha 5'):
		st.image('autobagger_semanal/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('autobagger_semanal/folha6.jpg')
				
	with st.beta_expander('Procedimentos folha 7'):
		st.image('autobagger_semanal/folha7.jpg')
				
	with st.beta_expander('Procedimentos folha 8'):
		st.image('autobagger_semanal/folha8.jpg')

	with st.beta_expander('Procedimentos folha 9'):
		st.image('autobagger_semanal/folha9.jpg')
				
	with st.beta_expander('Procedimentos folha 10'):
		st.image('autobagger_semanal/folha10.jpg')
				
	with st.beta_expander('Procedimentos folha 11'):
		st.image('autobagger_semanal/folha11.jpg')
				
	with st.beta_expander('Procedimentos folha 12'):
		st.image('autobagger_semanal/folha12.jpg')

def Autobagger_mensal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Guia linear (pivot bag tray) - Sistema de empacotamento (autobagger): Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
		T01.info('Guia linear (bag cheio) - Sistema de empacotamento (auto bagger): Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
		T02.info('Correia sincronizada (pick and place): Sistema de Alimentação de tampas. Inspeção da correia é realizada com a maquina parada realizando o bloqueio de energia (loto)verificando se possui algum desgaste.')
		T03.info('Rolos de transmissão: Transporte saída do pallet. Realizar limpeza/inspeção/lubrificação do rolos de transmissão tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio.')
		T04.info('Corrente (carriage lift) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
		T05.info('Mancal (carriage lift) Sistema de paletização do pallet: Sera realizado a limpeza do excesso de graxa do rolamento do mancal , inspeção visual do estado do rolamento e lubrificação adequada do mesmo, a atividade é realizada com a maquina parada realizando o bloqueio de energia(loto).')
		T06.info('Guia linear (Carriage) - Sistema de paletização do pallet: Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
		T07.info('Corrente transporte (Pallet conveyor) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
		T08.info('Corrente motora ( Pallet conveyor) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
		
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("autobagger_mensal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Autobagger_mensal_proc():
	with st.beta_expander('Pontos'):
		st.image('autobagger_mensal/Pontos autobagger mensal.jfif')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('autobagger_mensal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('autobagger_mensal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('autobagger_mensal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('autobagger_mensal/folha4.jpg')
		
	with st.beta_expander('Procedimentos folha 5'):
		st.image('autobagger_mensal/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('autobagger_mensal/folha6.jpg')
				
	with st.beta_expander('Procedimentos folha 7'):
		st.image('autobagger_mensal/folha7.jpg')
				
	with st.beta_expander('Procedimentos folha 8'):
		st.image('autobagger_mensal/folha8.jpg')

	with st.beta_expander('Procedimentos folha 9'):
		st.image('autobagger_mensal/folha9.jpg')
				
	with st.beta_expander('Procedimentos folha 10'):
		st.image('autobagger_mensal/folha10.jpg')
				
	with st.beta_expander('Procedimentos folha 11'):
		st.image('autobagger_mensal/folha11.jpg')
				
	with st.beta_expander('Procedimentos folha 12'):
		st.image('autobagger_mensal/folha12.jpg')
		
	with st.beta_expander('Procedimentos folha 13'):
		st.image('autobagger_mensal/folha13.jpg')
				
	with st.beta_expander('Procedimentos folha 14'):
		st.image('autobagger_mensal/folha14.jpg')
				
	with st.beta_expander('Procedimentos folha 15'):
		st.image('autobagger_mensal/folha15.jpg')
		
def balancer_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])

		# Texto das questões
		T00.info('Proteções e partes externas da máquina: 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe  alguma anomalia.')
		T01.info('Piso do interior da máquina: 1- Realizar a limpeza dos pontos de difícil acesso do piso e parte inferior da máquina com um soprador. Após soprar todas as tampas, utilizar vassoura e pá para recolher  e descarta-las em local adequado.')
		T02.info('Piso exterior da máquina: 1- Executar limpeza nos pontos externos de difícil acesso na parte inferior da máquina da máquina.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("balancer_diario").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def balancer_diario_proc():

	with st.beta_expander('Pontos'):
		st.image('balancer_diario/Pontos diario balancer.JPG')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('balancer_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('balancer_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('balancer_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('balancer_semanal/folha4.jpg')
        
def balancer_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Limpeza dos trilhos de transporte das tampas: 1- Limpar os trilhos com pano seco, após a limpeza observar se existem partes soltas ou com folga.')
		T01.info('Limpar o braço do robô: 1- Limpeza com pano umedecido em álcool isopropílico, nas articulações e espelhos dos sensores. Inspecionar toda a área se existe  alguma anomalia.')
		T02.info('Limpeza do painel de operação IHM: 1- Limpar com um pano seco toda a interface da IHM')
		T03.info("Limpeza do sistema de armazenamento / transferência de tampas nas tray's: 1- Executar limpeza do excesso de graxa dos rolamentos, mancais, limpeza dos rolos e correntes de transmissão. Limpar mesa de transferência e unidade de conservação.")
		T04.info('Finalizar a limpeza e colocar a máquina em operação: 1- Após o procedimento de limpeza conferir se não há componentes esquecidos dentro da máquina. Deve-se garantir que não haja ninguém dentro do perímetro de proteção da máquina. Seguir todo o procedimento de partida após intervenção na máquina.')
		T05.info('Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar pistola de ar')

			
		respostas = ['NOK', 'OK']

		# Questões
		
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
		
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("balancer_semanal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')
		
def balancer_semanal_proc():

	with st.beta_expander('Pontos'):
		st.image('balancer_semanal/Pontos semanal balancer.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('balancer_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('balancer_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('balancer_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('balancer_semanal/folha4.jpg')		

def conversion_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
	
		# Texto das questões
		T00.info('Die set superior/inferior Tab Die: 1- Utilize ar comprimido e  escova de bronze para remover excesso de alumínio ou impurezas das ferramentas e matriz do tab die.  Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T01.info('Die set superior/inferior Lane Die (1ª á 8ª estação): 1- Utilize ar comprimido e  escova de bronze para remover excesso de alumínio ou impurezas das ferramentas e matriz do tab die.  Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T02.info('Limpeza interior da máquina: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades. OBS: Atentar-se para não deixar ferramentas ou materiais de limpeza no interior da máquina.')
		T03.info('CILindro de acionamento da guarda: 1- Utilizando um pano limpo com solvente, deve-se limpar toda a região e logo após soprar com ar comprimido para secar. Realizar inspeção das guardas para detecção de possíveis anomalias.')
		T04.info('Limpar câmara interna do MLT: 1- Limpar câmara interna somente com água.')
		T05.info('Limpeza da mesa TAB Uncoiler: 1- Limpar com pano umedecido com álcool isopropílico e inspecionar possíveis anomalias ou anormalidades.')
		T06.info('Limpeza nas proteções acrílicas na área do Downstacker: 1- Limpar com pano umedecido com álcool isopropílico  e inspecionar possíveis anomalias ou anormalidades.')
		T07.info('Drenar o óleo da canaleta na parte frontal e traseira da máquina.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("conversion_diario").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')
                        
def conversion_diario_proc():
	with st.beta_expander('Pontos'):
		st.image('conversion_diario/Pontos diario conversion.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('conversion_diario/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('conversion_diario/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('conversion_diario/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('conversion_diario/folha4.jpg')
				
	with st.beta_expander('Procedimentos folha 5'):
		st.image('conversion_diario/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('conversion_diario/folha6.jpg')
        
	with st.beta_expander('Procedimentos folha 7'):
		st.image('conversion_diario/folha7.jpg')
				
	with st.beta_expander('Procedimentos folha 8'):
		st.image('conversion_diario/folha8.jpg')
				
	with st.beta_expander('Procedimentos folha 9'):
		st.image('conversion_diario/folha9.jpg')
				
	with st.beta_expander('Procedimentos folha 10'):
		st.image('conversion_diario/folha10.jpg')
				
	with st.beta_expander('Procedimentos folha 11'):
		st.image('conversion_diario/folha11.jpg')

		
def conversion_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		T09, Q09, C09 = st.beta_columns([3,1,3])
		T10, Q10, C10 = st.beta_columns([3,1,3])
		T11, Q11, C11 = st.beta_columns([3,1,3])
		T12, Q12, C12 = st.beta_columns([3,1,3])
		T13, Q13, C13 = st.beta_columns([3,1,3])
		T14, Q14, C14 = st.beta_columns([3,1,3])
		T15, Q15, C15 = st.beta_columns([3,1,3])
		T16, Q16, C16 = st.beta_columns([3,1,3])
		T17, Q17, C17 = st.beta_columns([3,1,3])
		T18, Q18, C18 = st.beta_columns([3,1,3])
		T19, Q19, C19 = st.beta_columns([3,1,3])
		T20, Q20, C20 = st.beta_columns([3,1,3])
		T21, Q21, C21 = st.beta_columns([3,1,3])
		T22, Q22, C22 = st.beta_columns([3,1,3])
		T23, Q23, C23 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('''Limpeza dentro da máquina: 
                1- Limpeza da parte interna da máquina com ar comprimido. Limpeza das ferramentas de matriz Tab die e Lane die com pano umedecido em álcool isopropílico e escova de bronze . Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.
                2- Remoção de materiais estranhos, panos, cavacos, sucata e outros que possam ter acumulado dentro da máquina;
                3- Limpeza das linhas de retorno de lubrificação se estiverem restringindo  fluxo de óleo.''')
		T01.info('''Limpeza do tab  uncoiler:
                1- Desconectar a energia principal do desenrolador antes de ficar na mesa do desenrolador de guias.'
                2 - Soprar e limpar o desbobinador de material da guia, o braço de dança, o painel de controle elétrico e o rolo / alimentador de compressão do material da guia.
                3 - Limpar somente quando estiver ocorrendo troca do bobina do Tab.''')
		T02.info('Bomba de circulação: 1-Inspecionar visualmente para detectar possíveis vazamentos.')
		T03.info('União Rotativa (Embreagem/Freio): 1-Inspecionar visualmente para detectar possíveis vazamentos.')
		T04.info('Limpeza da Conveyor #1 BB-CP e Pushers no mesanino: 1- Limpar com um pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T05.info('Limpeza da Conveyor #2 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T06.info('Limpeza da Conveyor #3 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T07.info('Limpeza da Conveyor #4 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T08.info('Limpeza das correias transportadoras dos 4 lanes 1º e 2º estagio: 1-Inpecionar quanto a integridade e executar a limpeza do mesmo.')
		T09.info('Limpeza das correias transportadoras dos 4 lanes 1º e 2º estagio: 1-Inpecionar quanto a integridade e executar a limpeza do mesmo.')
		T10.info('Limpar o Downstacker: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T11.info('Limpeza Light Test. (Suporte do Técnico Eletrônico): 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T12.info('Limpeza do ferramental da 6ª estação (Formação do Rebite): 1- Limpeza com álcool e escova todas as ferramentas superiores e inferiores do Lane e Tab Die.')
		T13.info('Limpeza da área do Gap Control e Downstacker: 1- Limpeza com pano seco.')
		T14.info('Limpar os filtros da bomba de vácuo. Da câmara de 1ª a 5ª e 7ª e 8ª estação inferior: 1- Limpar com pano umedecido com álcool isopropílico.')
		T15.info('Limpeza na estrutura da máquina. (base, piso, laterais, acrílicos e etc): 1- Retirar as tampas que estiverem no chão. Utilizando soprador, vassoura e pá e verificar o sistema quanto a presença de vazamentos na area externa e possíveis anomalias.')
		T16.info('Inspecionar e limpar se necessário as mangueiras da 6ª estação: 1- Limpar com pano umedecido.')
		T17.info('Inspecionar e limpar se necessário as mangueiras de vácuo do Lane Die: 1- Limpar com pano umedecido.')
		T18.info('Limpeza das guardas de proteção da Prensa: 1-Limpar com pano umedecido  com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
		T19.info('Limpeza das bancadas de lançamentos de dados e bancadas de retrabalho: 1- Limpar com  pano umedecido com álcool isopropílico.')
		T20.info('Inspecionar e limpar Conveyor #1 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
		T21.info('Inspecionar e limpar Conveyor #2 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
		T22.info('Inspecionar e limpar Conveyor #3 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
		T23.info('Inspecionar e limpar Conveyor #4 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.radio('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.radio('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.radio('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.radio('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.radio('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.radio('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.radio('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.radio('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.radio('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.radio('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		dic['Q19'] = Q19.radio('Item 19:', respostas)
		dic['C19'] = C19.text_input('Comentário item 19:', "")
		dic['Q20'] = Q20.radio('Item 20:', respostas)
		dic['C20'] = C20.text_input('Comentário item 20:', "")
		dic['Q21'] = Q21.radio('Item 21:', respostas)
		dic['C21'] = C21.text_input('Comentário item 21:', "")
		dic['Q22'] = Q22.radio('Item 22:', respostas)
		dic['C22'] = C22.text_input('Comentário item 22:', "")
		dic['Q23'] = Q23.radio('Item 23:', respostas)
		dic['C23'] = C23.text_input('Comentário item 23:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("conversion_semanal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')
            
            
def conversion_semanal_proc():
	with st.beta_expander('Pontos'):
		st.image('conversion_semanal/Pontos semanal conversion.jfif')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('conversion_semanal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('conversion_semanal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('conversion_semanal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('conversion_semanal/folha4.jpg')
				
	with st.beta_expander('Procedimentos folha 5'):
		st.image('conversion_semanal/folha5.jpg')
				
	with st.beta_expander('Procedimentos folha 6'):
		st.image('conversion_semanal/folha6.jpg')
			
def conversion_mensal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		dic['I0' ] = st.selectbox('Nome do colaborador', nomes)
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		T06, Q06, C06 = st.beta_columns([3,1,3])
		T07, Q07, C07 = st.beta_columns([3,1,3])
		T08, Q08, C08 = st.beta_columns([3,1,3])
		T09, Q09, C09 = st.beta_columns([3,1,3])
		T10, Q10, C10 = st.beta_columns([3,1,3])
		T11, Q11, C11 = st.beta_columns([3,1,3])
		T12, Q12, C12 = st.beta_columns([3,1,3])
		T13, Q13, C13 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Válvula direcional feed roll (tab feed roll): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T01.info('CILindro tensionador da transfer belt: Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
		T02.info('Válvula direcional do cilindro do freio da lâmina (stock stop): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T03.info('CILindro (Stock Stop): Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
		T04.info('Válvula direcional (CILindro da guarda): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T05.info('CILindro de acionamento da guarda: Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
		T06.info('Válvula de bloqueio: Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T07.info('Válvula do lubrifil: Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T08.info('Filtro de ar: Verificar visualmente se existe algum desgaste.')
		T09.info('Válvula reguladora de pressão: Verificar visualmente se existe algum desgaste.')
		T10.info('Válvula de acionamento (tensionamento do cilindro da transfer belt): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
		T11.info('Mangueiras e conexões pneumáticas: Verificar se há vazamentos de ar na s mangueiras e conexões pneumáticas')
		T12.info('Sistema de vácuo: Inspecionar quanto a integridade e executar a limpeza do mesmo.')
		T13.info('Correia de transporte do conveyor: Inspecionar quanto a integridade e executar a limpeza do mesmo.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I2' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()
		
		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['I1' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['I1' ] = 'Turno B'
		else:
			dic['I1' ] = 'Turno C'
            
		dic['Q00'] = Q00.radio('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.radio('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.radio('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.radio('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.radio('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.radio('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.radio('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.radio('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.radio('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.radio('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.radio('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.radio('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.radio('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.radio('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		
		submitted = st.form_submit_button('Enviar formulário')
		
	# Envio do formulário
	if submitted:

		# Limpa cache
		caching.clear_cache()
		
		# Transforma dados do formulário em um dicionário
		keys_values = dic.items()
		new_d = {str(key): str(value) for key, value in keys_values}

		# Verifica campos não preenchidos e os modifica
		for key, value in new_d.items():
			if (value == '') or value == '[]':
				new_d[key] = '-'
		
		# Define o nome do documento a ser armazenado no banco
		val_documento = new_d['I2'] + new_d['I1']

		# Armazena no banco
		try:
			doc_ref = db.collection("conversion_mensal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')
            
def conversion_mensal_proc():
	with st.beta_expander('Pontos'):
		st.image('conversion_mensal/Pontos mensal conversion.jfif')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('conversion_mensal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('conversion_mensal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('conversion_mensal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('conversion_mensal/folha4.jpg')
		
##################################################################################################
#			Formularios de troubleshooting
##################################################################################################

def trouble_liner():
	df = pd.read_csv("troubleshoot_csv/liner.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='liner1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='liner2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Avaliando causa e solução')
		if df_nv2.shape[0] > 0:
			_st3, _st4 = st.beta_columns(2)

			causa = _st3.radio('3) Causa', list(df_nv2['Causa'].unique()), key='liner3')
			df_causa = df_nv2[df_nv2['Causa'] == causa]

			solucao = _st4.radio('4) Solução', list(df_nv2['Solucao'].unique()), key='liner4')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes) 
		
		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = causa
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Liner'
		enviar_troubleshoot(dic, "troubleshoot")

def test():
	pass	

def trouble_shell():
	df = pd.read_csv("troubleshoot_csv/shell.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='shell1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='shell2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Avaliando causa e solução')
		if df_nv2.shape[0] > 0:
			_st3, _st4 = st.beta_columns(2)

			causa = _st3.radio('3) Causa', list(df_nv2['Causa'].unique()), key='shell3')
			df_causa = df_nv2[df_nv2['Causa'] == causa]

			solucao = _st4.radio('4) Solução', list(df_nv2['Solucao'].unique()), key='shell4')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = causa
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Shell'          
		enviar_troubleshoot(dic, "troubleshoot")

def trouble_autobagger():
	df = pd.read_csv("troubleshoot_csv/autobagger.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='auto1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='auto2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Possíveis soluções')
		if df_nv2.shape[0] > 0:

			solucao = st.radio('3) Solução', list(df_nv2['Solucao'].unique()), key='auto3')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)
   
		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = '-'
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Autobagger'
		enviar_troubleshoot(dic, "troubleshoot")
	
def trouble_conversion():
	df = pd.read_csv("troubleshoot_csv/conversion.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='conv1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='conv2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Possíveis soluções')
		if df_nv2.shape[0] > 0:

			solucao = st.radio('3) Solução', list(df_nv2['Solucao'].unique()), key='conv3')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = '-'
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Conversion'
		enviar_troubleshoot(dic, "troubleshoot")
	
def trouble_balancer_a():
	pass
	
def trouble_balancer_b():
	pass
	
def trouble_gfs():		
	df = pd.read_csv("troubleshoot_csv/gfs.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='gfs1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='gfs2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Possíveis soluções')
		if df_nv2.shape[0] > 0:

			solucao = st.radio('3) Solução', list(df_nv2['Solucao'].unique()), key='gfs3')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = '-'
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'GFS'
		enviar_troubleshoot(dic, "troubleshoot")
		
def trouble_dry():
	df = pd.read_csv("troubleshoot_csv/dry.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='dry1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='dry2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Avaliando causa e solução')
		if df_nv2.shape[0] > 0:
			_st3, _st4 = st.beta_columns(2)

			causa = _st3.radio('3) Causa', list(df_nv2['Causa'].unique()), key='dry3')
			df_causa = df_nv2[df_nv2['Causa'] == causa]

			solucao = _st4.radio('4) Solução', list(df_nv2['Solucao'].unique()), key='dry4')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = causa
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Dry Oven'
		enviar_troubleshoot(dic, "troubleshoot")
	
def trouble_tab():
	df = pd.read_csv("troubleshoot_csv/tab.csv", sep=';')

	st.subheader('Identificando o problema')

	nv1 = st.selectbox('1) Qual o tipo do problema?', list(df['Nv1'].unique()) , key='tab1')
	df_nv1 = df[df['Nv1'] == nv1]

	if df_nv1.shape[0] > 0:
		nv2 = st.selectbox('2) Qual o problema?', list(df_nv1['Nv2'].unique()),  key='tab2')
		df_nv2 = df_nv1[df_nv1['Nv2'] == nv2]

		st.subheader('Avaliando causa e solução')
		if df_nv2.shape[0] > 0:
			_st3, _st4 = st.beta_columns(2)

			causa = _st3.radio('3) Causa', list(df_nv2['Causa'].unique()), key='tab3')
			df_causa = df_nv2[df_nv2['Causa'] == causa]

			solucao = _st4.radio('4) Solução', list(df_nv2['Solucao'].unique()), key='tab4')
	
	with st.form('Form'):
		s1, s2,  = st.beta_columns([2,8])
		dic['Nome'] = st.selectbox('Nome do colaborador', nomes)

		dic['Resolveu'] = s1.selectbox('Resolveu o problema?', ['Não', 'Sim'])
		dic['Comentario'] = s2.text_input('Comentário')

		# definição da hora e turno
		dic['Data' ] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
		hora_atual = datetime.now(tz).time()

		if (hora_atual >= time(23, 0, 0)) | (hora_atual < time(7, 0, 0)):
			dic['Turno' ] = 'Turno A'
		elif (hora_atual >= time(7, 0, 0)) & (hora_atual < time(15, 0, 0)):
			dic['Turno' ] = 'Turno B'
		else:
			dic['Turno' ] = 'Turno C'

		submitted = st.form_submit_button('Enviar Troubleshoot')
		
	# Envio do formulário
	if submitted:
		dic['Nv1'] = nv1
		dic['Nv2'] = nv2
		dic['Causa'] = causa
		dic['Solucao'] = solucao
		dic['Equipamento'] = 'Tab Uncoiler'
		enviar_troubleshoot(dic, "troubleshoot")

def enviar_troubleshoot(dic, colecao):

	# Limpa cache
	caching.clear_cache()

	# Transforma dados do formulário em um dicionário
	keys_values = dic.items()
	new_d = {str(key): str(value) for key, value in keys_values}

	# Verifica campos não preenchidos e os modifica
	for key, value in new_d.items():
		if (value == '') or value == '[]':
			new_d[key] = '-'

	# Armazena no banco
	try:
		doc_ref = db.collection(colecao).document()
		doc_ref.set(new_d)
		st.success('Formulário armazenado com sucesso!')
	except:
		st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')
		
######################################################################################################
                                           #Main
######################################################################################################

if __name__ == '__main__':
	# Carrega dados dos colaboradores
	usuarios = load_users()

	# Constantes
	turnos = ['Turno A', 'Turno B', 'Turno C']
	nomes = list(usuarios.iloc[:,2])

	# coleta os formularios do banco
	df_cil_liner_d = load_forms_cil('Liner_diario')
	df_cil_shell_d = load_forms_cil('shell_diario')
	df_cil_auto_d = load_forms_cil('autobagger_diario')
	df_cil_conv_d = load_forms_cil('conversion_diario')
	df_cil_bala_d = load_forms_cil('balancer_diario')
	df_cil_liner_s = load_forms_cil('Liner_semanal')
	df_cil_shell_s = load_forms_cil('shell_semanal')
	df_cil_auto_s = load_forms_cil('autobagger_semanal')
	df_cil_conv_s = load_forms_cil('conversion_semanal')
	df_cil_bala_s = load_forms_cil('balancer_semanal')
	df_cil_auto_m = load_forms_cil('autobagger_mensal')
	df_cil_conv_m = load_forms_cil('conversion_mensal')	

	# Lista vazia para input dos dados do formulário
	dic = {} #dicionario

	##################################################################################################
	#			Chamadada das páginas do cil
	##################################################################################################
	
	if func_escolhida == 'Liner diário':
		st.subheader('Liner diário')
		
		proc_LD = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LD:
			Liner_diario_proc()
		Liner_diario()
		
	if func_escolhida == 'Liner semanal':
		st.subheader('Liner semanal')
		
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Liner_semanal_proc()
		Liner_semanal()
		
	if func_escolhida == 'Shell diário':
		st.subheader('Shell diário')
		proc_SD = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_SD:
			Shell_diario_proc()
		Shell_diario()
		
	if func_escolhida == 'Shell semanal':
		st.subheader('Shell semanal')
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Shell_semanal_proc()
		Shell_semanal()
		
	if func_escolhida == 'Autobagger diário':
		st.subheader('Autobagger diário')
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Autobagger_diario_proc()
		Autobagger_diario()
		
	if func_escolhida == 'Autobagger semanal':
		st.subheader('Autobagger semanal')
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Autobagger_semanal_proc()
		Autobagger_semanal()
		
	if func_escolhida == 'Autobagger mensal':
		st.subheader('Autobagger mensal')
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Autobagger_mensal_proc()
		Autobagger_mensal()
		
	if func_escolhida == 'Conversion diário':
		st.subheader('Conversion diário')
		proc_CD = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_CD:
			conversion_diario_proc()
		conversion_diario()
		
	if func_escolhida == 'Conversion semanal':
		st.subheader('Conversion semanal')
		proc_CS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_CS:
			conversion_semanal_proc()
		conversion_semanal()
			
	if func_escolhida == 'Conversion mensal':
		st.subheader('Conversion mensal')
		proc_CM = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_CM:
			conversion_mensal_proc()
		conversion_mensal()
		
	if func_escolhida == 'Balancer diário':
		st.subheader('Balancer diário')
		proc_BD = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_BD:
			balancer_diario_proc()
		balancer_diario()
		
	if func_escolhida == 'Balancer semanal':
		st.subheader('Balancer semanal')
		proc_BS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_BS:
			balancer_semanal_proc()
		balancer_semanal()
		
	##################################################################################################
	#			Chamada das páginas do troubleshooting
	##################################################################################################
		
	if func_escolhida == 'Liner':
		st.subheader('Troubleshooting Liner')	
		trouble_liner()
		
	if func_escolhida == 'Shell Press':
		st.subheader('Troubleshooting Shell Press')
		trouble_shell()

	if func_escolhida == 'Autobagger':
		st.subheader('Troubleshooting Autobagger')
		trouble_autobagger()
		
	if func_escolhida == 'Conversion Press':
		st.subheader('Troubleshooting Conversion Press')	
		trouble_conversion()
		
	if func_escolhida == 'Balancer A':
		st.subheader('Troubleshooting Balancer A')
		trouble_balancer_a()
		
	if func_escolhida == 'Balancer B':
		st.subheader('Troubleshooting Balancer B')
		trouble_balancer_b()
		
	if func_escolhida == 'GFS':
		st.subheader('Troubleshooting GFS')
		trouble_gfs()
		
	if func_escolhida == 'Dry Oven':
		st.subheader('Troubleshooting Dry Oven')
		trouble_dry()
		
	if func_escolhida == 'Tab Uncoiler':
		st.subheader('Troubleshooting Tab Uncoiler')
		trouble_tab()
		
	##################################################################################################
	#			Demais funcionalidades
	##################################################################################################
		
	if func_escolhida ==  'Visualizar formulários':
		form_selecionado = st.selectbox('Selecione o tipo de formulário que deseja visualizar', formularios_cil_2)
		
		if form_selecionado == 'Liner diário':
			df_cil = load_forms_cil('Liner_diario')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				# Texto das questões
				st.info('Q00) Retirar a escova do suporte, depositar a escova dentro do recipiente com solução de limpeza durante 30 minutos.  Inspecionar as escovas para detectar possíveis anomalias e desgastes.')
				st.info('Q01) Limpeza das guias de saída: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar as saídas para detectar possíveis anomalias e desgastes.')
				st.info('Q02) Limpeza do conjunto Lower Turret e Upper Turret: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar o conjunto para detectar possíveis anomalias e desgastes.')
				st.info('Q03) Limpeza da mesa e da Star Wheel: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico. Inspecionar a mesa para detectar possíveis anomalias e desgastes.')
				st.info('Q04) Limpeza ao redor do piso do equipamento: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
				st.info('Q05) Limpeza Balancer "B": 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
				st.info('Q06) Limpeza do visor da estação de aplicação de vedante: 1-Limpeza do superfície utilizando pano umedecido com álcool isopropílico.')
				st.info('Q07) Limpeza nos furos do Hopper: 1-Limpeza utilizando pano umedecido com álcool isopropílico.')
				st.info('Q08) Limpeza na calha de rejeito das  correias transportadoras: 1-Limpeza utilizando pano umedecido com álcool isopropílico.')

		if form_selecionado == 'Liner semanal':
			df_cil = load_forms_cil('Liner_semanal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q10', 'Q11', 'Q12',  'Q13', 'Q14', 'Q15', 'Q16', 'Q17','Q18', 'Q19', 'Q20', 'Q21', 'Q22',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',  'C13', 'C14', 'C15', 'C16', 'C17','C18', 'C19', 'C20', 'C21', 'C22',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				# Texto das questões
				st.info('Q00) Limpeza Conveyor #1 BALN e Pushers 1,2,3,4: 1- Limpar com pano umedecido  e álcool isopropílico.')
				st.info('Q01) Limpeza Conveyor #2 BA-LN e Pushers 1,2,3,4: 1- Limpar com pano umedecido  e álcool isopropílico.')
				st.info('Q02) Limpeza Conveyor #3 BA-LN e Pushers 1,2,3,4,5: 1- Limpar com pano umedecido  e álcool isopropílico.')
				st.info('Q03) Limpeza Conveyor #4 BA-LN e Pushers 1,2,3,4,5: 1- Limpar com pano umedecido  e álcool isopropílico.')
				st.info('Q04) Limpeza Conveyor #4 BA-LN e Pushers 1,2,3,4,5,6: 1- Limpar com pano umedecido  e álcool isopropílico.')
				st.info('Q05) Limpeza da esteira de alimentação:  1-Limpar a superfície utilizando pano umedecido com álcool isopropílico. Inspecionar a esteira para detectar possíveis anomalias e desgastes.')
				st.info('Q06) Desmontagem e limpeza do Downstacker: 1- Limpar o seu interior com o auxílio de um aspirador pneumático, após limpe com um pano umedecido  em álcool isopropílico toda a área aspirada. Inspecionar o equipamento para detectar possíveis anomalias e desgastes.')
				st.info('Q07) Limpeza da mesa e da Star Wheel: 1- Limpar com pano umedecido em álcool isopropílico toda a superfície da mesa do Lower Turret que ainda não foi limpa, se necessário utilize a haste metálica pontiaguda para retirar compound preso nas juntas ou fissuras  Limpe toda a face da Star Wheel. Limpe as portas/gaiolas de proteção do lado externo e interno.')
				st.info('Q08) Limpeza da caixa de óleo: 1- Limpar com pano umedecido em álcool isopropílico as laterais do lado de dentro da caixa de gotejamento de óleo. Não é necessário fazer sangria ou limpar o fundo/parte de baixo da caixa.')
				st.info('Q09) Limpeza da correia transportadora de saída do Liner: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q10) Limpeza das guias de descargas: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q11) Limpeza da Plate Turrent Suport, Seal Retainer e Lower Chuck: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q12) Limpeza dos Hopper: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q13) Limpeza na estrutura dos fornos e pisos: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q14) Limpeza nas estruturas da máquina: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q15) Limpeza nos pushers do mezanino e nos pushers após o Hopper na parte de baixo proximo ao piso: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q16) Limpeza da guarda pelo lado interno: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q17) Limpeza da Conveyor #1 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q18) Limpeza da Conveyor #2 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q19) Limpeza da Conveyor #3 LN-BB e Pushers 1,2,3,4 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q20) Limpeza da Conveyor #4 LN-BB e Pushers 1,2,3 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q21) Limpeza da Conveyor #5 LN-BB e Pushers 1,2,3 no mesanino: 1-Limpar com pano umedecido em álcool isopropílico.')
				st.info('Q22) Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar água e pistola de ar.')

		if form_selecionado == 'Shell diário':
			df_cil = load_forms_cil('shell_diario')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q10', 'Q11', 'Q12',  'Q13', 'Q14', 'Q15', 'Q16', 'Q17','Q18',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',  'C13', 'C14', 'C15', 'C16', 'C17','C18',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				# Texto das questões
				st.info('Q00) Limpeza Sistema de curlers e sincronizers: 1- Limpeza com uma flanela umedecida em álcool isopropílico das mesas quatro mesas de curlers  e sincronizers removendo o pó de alumínio acumulado sobre os mesmos.')
				st.info('Q01) Limpeza da parte interna do ferramental: 1- Limpar com uma flanela umedecida em álcool isopropílico todo o perímetro do ferramental, removendo pó de alumínio e pequenas farpas que possam danificar as shells durante a produção. 2-Com uma flanela limpa umedecida em álcool isopropílico, limpar toda a região das hastes dos cilindros da guardas de proteção após a limpeza soprar com o ar comprimido para secar. 3-Inspecionar o upper die verificando a existência de vazamento nos sistemas hidráulico e pneumático. Obs: Executar a limpeza a cada troca de bobina e observar o esqueleto da chapa para identificar possíveis rebarbas no produto.')
				st.info('Q02) Limpeza dos blowers: 1. Com um flanela umedecida em álcool isopropílico limpar todas as saídas removendo toda sujidade.')
				st.info('Q03) CILindro do quick lifit: 1. Verificar quanto a vazamentos de óleo.')
				st.info('Q04) Unidade de ajuste de pressão (stand de ar): 1. Utilizando tato e audição verificar quanto a vazamentos.')
				st.info('Q05) Gaiola de esferas das colunas: 1-Verificar a eficiência da lubrificação do conjunto de guias, observando se há uma película fina de oleo e ausência de vazamentos.')
				st.info('Q06) Limpar o piso: 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
				st.info('Q07) Limpar área ao redor da prensa: 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
				st.info('Q08) Limpeza do painel de controle e bancadas: 1-Limpa com pano seco.')
				st.info('Q09) Limpeza no Balancer "A": 1- Limpeza com uma flanela umedecida em álcool isopropílico.')
				st.info('Q10) Limpeza da estrutura da máquina. (Acrílicos, Guarda Corpos, Proteções): 1-Limpeza com uma flanela umedecida em álcool isopropílico.')
				st.info('Q11) Limpeza nas partes acessíveis da prensa: 1- Limpar com uma flanela umedecida em álcool isopropílico todo o perímetro do ferramental, removendo pó de alumínio e pequenas farpas que possam danificar as shells durante a produção. Bloquei ode energia SAM/LOTOTO. Realizar o bloqueio de energia e verificar a eficácia do mesmo.')
				st.info('Q12) Preparação: Separar e conferir todas as ferramentas, materiais e produtos indicados no item nº 2 do procedimento.')
				st.info('Q13) Inspeção e limpeza do GFS: Utilizando um pano umedecido com álcool isopropílico, limpe os rolos do acumulador de loop. Após a limpeza, utilizando o tato, passe a mão em torno dos rolos a fim de detectar possíveis ondulações e pequenas protuberâncias nos rolos. Observar também a existência de componentes necessitando de reaperto.')
				st.info('Q14) Inspeção e limpeza do rolo de alimentação de lâmina: Utilizando um pano umedecido com álcool isopropílico, limpe os rolos do acumulador de loop. Após a limpeza, utilizando o tato, passe a mão em torno dos rolos a fim de detectar possíveis ondulações e pequenas protuberâncias nos rolos. Observar também a existência de componentes necessitando de reaperto.')
				st.info('Q15) Curler: Bloqueio de energia. Execute o bloquei ode energia conforme o procedimento e em seguida verifique a eficácia do mesmo.')
				st.info('Q16) Preparação: Preparar os materiais para a limpeza e inspeção.')
				st.info('Q17) Limpeza dos segmentos do Curler: Utilizando uma haste de latão, retire todas as tampas presas nos segmentos do Curler (se houver). Em seguida, aplique ar comprimido e limpe todos os segmentos com um pano umedecido em álcool isopropílico.')
				st.info('Q18) Limpeza externa: "Utilizando um pano umedecido em álcool isopropílico, limpe toda a parte externa do Curler como mesa, estrutura externa (com exceção das tampas de acrílico) a fim de remover toda a poeira presente. Para limpar as tampas de acrílico, utilize um pano seco e limpo a fim de remover toda a sujidade existente."')

		if form_selecionado == 'Shell semanal':
			df_cil = load_forms_cil('shell_semanal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q10', 'Q11', 'Q12',  'Q13', 'Q14', 'Q15', 'Q16', 'Q17','Q18', 'Q19', 'Q20', 
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',  'C13', 'C14', 'C15', 'C16', 'C17','C18', 'C19', 'C20',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				# Texto das questões
				st.info('Q00) Saída de shells para as curlers: 1-Limpar o sistema transporte das shells fazendo movimentos alternados de vai e vem nas 24 saídas de forma a retirar toda sujeira do percurso.')
				st.info('Q01) Sistema de scrap: 1-Limpar o sistema de scrap verificando sempre se não há nenhum resto de chapa ou shell presa no percurso do sistema.')
				st.info('Q02) Die set: 1-Remover as striper plate e stock plate; 2-Limpar todo perímetro do lower die e upper die ;3- Limpar a stipper plate e montar as mesmas no lower die; 4- Limpar a stock plate  e montar no upper die.')
				st.info('Q03) Sistema de vácuo: 1-Limpeza e inspeção das válvulas.')
				st.info('Q04) Pushers: 1-Descarregar os pushers e com uma flanela umedecida com álcool isopropílico limpar e inspecionar toda a parte interna e externa dos mesmos .')
				st.info('Q05) Air eject: 1-Checar visualmente as condições do componente, e utilizando o tato e audição para identificar possíveis vazamentos.')
				st.info('Q06) Limpeza na estrutura da máquina (bases, mangueiras, laterais, acrílicos, bancadas e piso): 1- Limpeza com pano umedecido e álcool isopropílico')
				st.info('Q07) Limpeza com ar nos segmentos do Curler: 1- Utilizar a pistola de ar.')
				st.info('Q08) Limpeza nas áreas dos Curlers (curlers, mesas, plataformas e tampas caídas): 1-Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q09) Limpeza dos synchronizers (limpar guardas, tampas caídas, hopper, armor start´s e passar escovas no Screws): 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q10) Limpar Conveyor #1 SP-BA e Pushers 1,2,3,4 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q11) Limpar Conveyor #2 SP-BA e Pushers 1,2,3,4 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q12) Limpeza Conveyor #3 SP-BA e Pushers 1,2,3,4,5 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q13) Limpeza Conveyor #4 SP-BA e Pushers 1,2,3,4,5 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q14) Limpeza Conveyor #5 SP-BA e Pushers 1,2,3 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q15) Limpeza Conveyor #6 SP-BA e Pushers 1,2,3 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q16) Limpeza Conveyor #7 SP-BA e Pushers 1,2 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q17) Limpeza Conveyor #8 SP-BA e Pushers 1,2 no mesanino: 1- Limpeza com pano umedecido em álcool isopropílico .')
				st.info('Q18) GFS Bloqueio de energia: Execute o bloqueio de energia conforme o padrão e testar a eficácia do mesmo. Preparar os materiais conforme a necessidade.')
				st.info('Q19) Limpeza parte externa da máquina: Limpar parte externa do equipamento utilizando pano umedecido com álcool isopropílico.')
				st.info('Q20) Unidade de conservação de Ar: Drenar a água do filtro da linha pneumática.')
			
		if form_selecionado == 'Autobagger diário':
			df_cil = load_forms_cil('autobagger_diario')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				st.info('Q00) Recolhimento de tampas (Autobagger Área do piso no entorno do equipamento, é área do piso interior do equipamento.): 1- Limpeza utilizando uma vassoura, pá e soprador de ar. Com as mãos, retire as tampas que ficaram presas dentro dos trays do Auto Bagger. Utilize o soprador para retirar as tampas do chão em parte de difícil acesso e logo após deve-se varrer e recolher as tampas utilizando a pá, e colocar no balde de scrap.')
				st.info('Q01) Proteções e parte externa das máquinas (Área do pallettizer / autobagger): 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe alguma anomalia.')
				st.info('Q02) Limpeza dos filtros (entrada e saída) - Autobagger e Palettizer Unidade de conservação (verificar a numeração em campo): 1- Limpeza de ambos os filtros (filtro de partículas e filtro coalescente) utilizando fluxo de ar e drenagem. Deve-se observar se os mesmos estão saturados, se caso estiver, devem ser trocados..')
				st.info('Q03) Temperatura do aquecedor (Autobagger Sistema de fechamento do Bag): 1- Realizar o check diário da correta especificação de temperatura.')
				st.info('Q04) Limpeza de todas as portas da área do Autobagger. 1- Limpar com pano  umedecido e álcool isopropílico.')
		
		if form_selecionado == 'Autobagger semanal':
			df_cil = load_forms_cil('autobagger_semanal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):

				st.info('Q00) Limpeza dos trilhos de transporte das tampas: 1- Limpar os trilhos com pano seco, após a limpeza observar se existem partes soltas ou com folga.')
				st.info('Q01) Limpar o braço do robô: 1- Limpeza com pano umedecido em álcool isopropílico, nas articulações e espelhos dos sensores. Inspecionar toda a área se existe  alguma anomalia.')
				st.info('Q02) Limpeza do painel de operação IHM: 1- Limpar com um pano seco toda a interface da IHM')
				st.info('Q03) Limpeza do sistema de armazenamento / transferência de tampas nas trays: 1- Executar limpeza do excesso de graxa dos rolamentos, mancais, limpeza dos rolos e correntes de transmissão. Limpar mesa de transferência e unidade de conservação.')
				st.info('Q04) Finalizar a limpeza e colocar a máquina em operação: 1- Após o procedimento de limpeza conferir se não há componentes esquecidos dentro da máquina. Deve-se garantir que não haja ninguém dentro do perímetro de proteção da máquina. Seguir todo o procedimento de partida após intervenção na máquina.')
				st.info('Q05) Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar pistola de ar.')
				
		if form_selecionado == 'Autobagger mensal':
			df_cil = load_forms_cil('autobagger_mensal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				st.info('Q00) Guia linear (pivot bag tray) - Sistema de empacotamento (autobagger): Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
				st.info('Q01) Guia linear (bag cheio) - Sistema de empacotamento (auto bagger): Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
				st.info('Q02) Correia sincronizada (pick and place): Sistema de Alimentação de tampas. Inspeção da correia é realizada com a maquina parada realizando o bloqueio de energia (loto)verificando se possui algum desgaste.')
				st.info('Q03) Rolos de transmissão: Transporte saída do pallet. Realizar limpeza/inspeção/lubrificação do rolos de transmissão tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio.')
				st.info('Q04) Corrente (carriage lift) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
				st.info('Q05) Mancal (carriage lift) Sistema de paletização do pallet: Sera realizado a limpeza do excesso de graxa do rolamento do mancal , inspeção visual do estado do rolamento e lubrificação adequada do mesmo, a atividade é realizada com a maquina parada realizando o bloqueio de energia(loto).')
				st.info('Q06) Guia linear (Carriage) - Sistema de paletização do pallet: Realizar limpeza/inspeção/lubrificação do Rolamento, tirando excesso de lubrificante e sujidades com o equipamento parado, devidamente com o bloqueio Loto.')
				st.info('Q07) Corrente transporte (Pallet conveyor) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
				st.info('Q08) Corrente motora ( Pallet conveyor) - Sistema de paletização do pallet: Realizar limpeza / inspeção / lubrificação do conjunto de transmissão da corrente, tirando o excesso de lubrificante e sujidades com o equipamento parado devidamente com o bloqueio loto.')
			
		if form_selecionado == 'Conversion diário':
			df_cil = load_forms_cil('conversion_diario')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06',]
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				st.info('Q00) Die set superior/inferior Tab Die: 1- Utilize ar comprimido e  escova de bronze para remover excesso de alumínio ou impurezas das ferramentas e matriz do tab die.  Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q01) Die set superior/inferior Lane Die (1ª á 8ª estação): 1- Utilize ar comprimido e  escova de bronze para remover excesso de alumínio ou impurezas das ferramentas e matriz do tab die.  Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q02) Limpeza interior da máquina: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades. OBS: Atentar-se para não deixar ferramentas ou materiais de limpeza no interior da máquina.')
				st.info('Q03) CILindro de acionamento da guarda: 1- Utilizando um pano limpo com solvente, deve-se limpar toda a região e logo após soprar com ar comprimido para secar. Realizar inspeção das guardas para detecção de possíveis anomalias.')
				st.info('Q04) Limpar câmara interna do MLT: 1- Limpar câmara interna somente com água.')
				st.info('Q05) Limpeza da mesa TAB Uncoiler: 1- Limpar com pano umedecido com álcool isopropílico e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q06) Limpeza nas proteções acrílicas na área do Downstacker: 1- Limpar com pano umedecido com álcool isopropílico  e inspecionar possíveis anomalias ou anormalidades.')
			
		if form_selecionado == 'Conversion semanal':
			df_cil = load_forms_cil('conversion_semanal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q10', 'Q11', 'Q12',  'Q13', 'Q14', 'Q15', 'Q16', 'Q17','Q18', 'Q19', 'Q20', 'Q21', 'Q22', 'Q23', 
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',  'C13', 'C14', 'C15', 'C16', 'C17','C18', 'C19', 'C20', 'C21', 'C22', 'C23']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				st.info('''Q00) Limpeza dentro da máquina: 
					1- Limpeza da parte interna da máquina com ar comprimido. Limpeza das ferramentas de matriz Tab die e Lane die com pano umedecido em álcool isopropílico e escova de bronze . Limpar a parte interna da máquina e inspecionar possíveis anomalias ou anormalidades.
					2- Remoção de materiais estranhos, panos, cavacos, sucata e outros que possam ter acumulado dentro da máquina;
					3- Limpeza das linhas de retorno de lubrificação se estiverem restringindo  fluxo de óleo.''')
				st.info('''Q01) Limpeza do tab  uncoiler:
					1- Desconectar a energia principal do desenrolador antes de ficar na mesa do desenrolador de guias.'
					2 - Soprar e limpar o desbobinador de material da guia, o braço de dança, o painel de controle elétrico e o rolo / alimentador de compressão do material da guia.
					3 - Limpar somente quando estiver ocorrendo troca do bobina do Tab.''')
				st.info('Q02) Bomba de circulação: 1-Inspecionar visualmente para detectar possíveis vazamentos.')
				st.info('Q03) União Rotativa (Embreagem/Freio): 1-Inspecionar visualmente para detectar possíveis vazamentos.')
				st.info('Q04) Limpeza da Conveyor #1 BB-CP e Pushers no mesanino: 1- Limpar com um pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q05) Limpeza da Conveyor #2 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q06) Limpeza da Conveyor #3 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q07) Limpeza da Conveyor #4 BB-CP e Pushers no mesanino: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q08) Limpeza das correias transportadoras dos 4 lanes 1º e 2º estagio: 1-Inpecionar quanto a integridade e executar a limpeza do mesmo.')
				st.info('Q09) Limpeza das correias transportadoras dos 4 lanes 1º e 2º estagio: 1-Inpecionar quanto a integridade e executar a limpeza do mesmo.')
				st.info('Q10) Limpar o Downstacker: 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q11) Limpeza Light Test. (Suporte do Técnico Eletrônico): 1- Limpar com pano umedecido com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q12) Limpeza do ferramental da 6ª estação (Formação do Rebite): 1- Limpeza com álcool e escova todas as ferramentas superiores e inferiores do Lane e Tab Die.')
				st.info('Q13) Limpeza da área do Gap Control e Downstacker: 1- Limpeza com pano seco.')
				st.info('Q14) Limpar os filtros da bomba de vácuo. Da câmara de 1ª a 5ª e 7ª e 8ª estação inferior: 1- Limpar com pano umedecido com álcool isopropílico.')
				st.info('Q15) Limpeza na estrutura da máquina. (base, piso, laterais, acrílicos e etc): 1- Retirar as tampas que estiverem no chão. Utilizando soprador, vassoura e pá e verificar o sistema quanto a presença de vazamentos na area externa e possíveis anomalias.')
				st.info('Q16) Inspecionar e limpar se necessário as mangueiras da 6ª estação: 1- Limpar com pano umedecido.')
				st.info('Q17) Inspecionar e limpar se necessário as mangueiras de vácuo do Lane Die: 1- Limpar com pano umedecido.')
				st.info('Q18) Limpeza das guardas de proteção da Prensa: 1-Limpar com pano umedecido  com álcool isopropílico o interior da máquina e inspecionar possíveis anomalias ou anormalidades.')
				st.info('Q19) Limpeza das bancadas de lançamentos de dados e bancadas de retrabalho: 1- Limpar com  pano umedecido com álcool isopropílico.')
				st.info('Q20) Inspecionar e limpar Conveyor #1 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
				st.info('Q21) Inspecionar e limpar Conveyor #2 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
				st.info('Q22) Inspecionar e limpar Conveyor #3 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
				st.info('Q23) Inspecionar e limpar Conveyor #4 CP-PK e Pushers 1,2: 1-Inspecionar e limpar com pano umedecido com álcool isopropílico.')
			
		if form_selecionado == 'Conversion mensal':
			df_cil = load_forms_cil('conversion_mensal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q10', 'Q11', 'Q12',  'Q13', 
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12',  'C13']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):

				st.info('Q00) Válvula direcional feed roll (tab feed roll): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q01) CILindro tensionador da transfer belt: Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
				st.info('Q02) Válvula direcional do cilindro do freio da lâmina (stock stop): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q03) CILindro (Stock Stop): Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
				st.info('Q04) Válvula direcional (CILindro da guarda): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q05) CILindro de acionamento da guarda: Inspeção no cilindro afim de verificar algum desgaste ou vazamento.')
				st.info('Q06) Válvula de bloqueio: Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q07) Válvula do lubrifil: Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q08) Filtro de ar: Verificar visualmente se existe algum desgaste.')
				st.info('Q09) Válvula reguladora de pressão: Verificar visualmente se existe algum desgaste.')
				st.info('Q10) Válvula de acionamento (tensionamento do cilindro da transfer belt): Inspeção das vedações afim de verificar algum desgaste ou vazamento.')
				st.info('Q11) Mangueiras e conexões pneumáticas: Verificar se há vazamentos de ar na s mangueiras e conexões pneumáticas')
				st.info('Q12) Sistema de vácuo: Inspecionar quanto a integridade e executar a limpeza do mesmo.')
				st.info('Q13) Correia de transporte do conveyor: Inspecionar quanto a integridade e executar a limpeza do mesmo.')
			
		if form_selecionado == 'Balancer diário':
			df_cil = load_forms_cil('balancer_diario')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 
					 'C00', 'C01', 'C02']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):
				
				st.info('Q00) Proteções e partes externas da máquina: 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe  alguma anomalia.')
				st.info('Q01) Piso do interior da máquina: 1- Realizar a limpeza dos pontos de difícil acesso do piso e parte inferior da máquina com um soprador. Após soprar todas as tampas, utilizar vassoura e pá para recolher  e descarta-las em local adequado.')
				st.info('Q02) Piso exterior da máquina: 1- Executar limpeza nos pontos externos de difícil acesso na parte inferior da máquina da máquina.')
			              
		if form_selecionado == 'Balancer semanal':
			df_cil = load_forms_cil('balancer_semanal')
			
			# Lista e ordena as colunas do dataframe
			lista_colunas = ['I2', 'I0', 'I1',
					 'Q00', 'Q01', 'Q02', 'Q03',  'Q04', 'Q05',
					 'C00', 'C01', 'C02', 'C03',  'C04', 'C05']
			df_cil = df_cil.reindex(columns=lista_colunas)
			
			with st.beta_expander('Visualizar as questões?'):

				st.info('Q00) Limpeza dos trilhos de transporte das tampas: 1- Limpar os trilhos com pano seco, após a limpeza observar se existem partes soltas ou com folga.')
				st.info('Q01) Limpar o braço do robô: 1- Limpeza com pano umedecido em álcool isopropílico, nas articulações e espelhos dos sensores. Inspecionar toda a área se existe  alguma anomalia.')
				st.info('Q02) Limpeza do painel de operação IHM: 1- Limpar com um pano seco toda a interface da IHM')
				st.info("Q03) Limpeza do sistema de armazenamento / transferência de tampas nas tray's: 1- Executar limpeza do excesso de graxa dos rolamentos, mancais, limpeza dos rolos e correntes de transmissão. Limpar mesa de transferência e unidade de conservação.")
				st.info('Q04) Finalizar a limpeza e colocar a máquina em operação: 1- Após o procedimento de limpeza conferir se não há componentes esquecidos dentro da máquina. Deve-se garantir que não haja ninguém dentro do perímetro de proteção da máquina. Seguir todo o procedimento de partida após intervenção na máquina.')
				st.info('Q05) Limpeza do filtro AIRCON painel elétrico, na alimentação de entrada: 1- Utilizar pistola de ar')
		
		col1, col2, _turno, _nome = st.beta_columns([2,2,3,9])
		inicio_filtro = col1.date_input("Início (ano/mês/dia)", datetime(2021, 7, 1))
		fim_filtro = col2.date_input("Fim (ano/mês/dia)")
		df_cil_filt = (df_cil[(df_cil['I2'].dt.date >= inicio_filtro) & (df_cil['I2'].dt.date <= fim_filtro)]) 

		# Gera lista dos turnos
		list_turno = list(df_cil_filt['I1'].drop_duplicates())
		list_turno.append('todos') 
		turno_filter = _turno.selectbox("Selecione o turno", list_turno, list_turno.index('todos'))
		
		# Inicia o filtro com todos
		if turno_filter == 'todos':
			pass
		elif turno_filter is not None and (str(turno_filter) != 'nan'):
			df_cil_filt = df_cil_filt[df_cil_filt['I1'] == equip]

		# Gera lista dos gestor	
		list_nome = list(df_cil_filt['I0'].drop_duplicates())
		list_nome.append('todos')  
		colaborador = _nome.selectbox("Selecione o colaborador", list_nome, list_nome.index('todos'))
		
		# Inicia o filtro com todos
		if colaborador == 'todos':
			pass
		elif colaborador is not None and (str(colaborador) != 'nan'):
			df_cil_filt = df_cil_filt[df_cil_filt['I0'] == colaborador]		
		
		gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules = config_grid(df_cil, False)
		response = AgGrid(
			    df_cil_filt, 
			    gridOptions=gridOptions,
			    height=grid_height, 
			    width='100%',
			    data_return_mode=return_mode_value, 
			    update_mode=update_mode_value,
			    fit_columns_on_grid_load=fit_columns_on_grid_load,
			    allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
			    enable_enterprise_modules=enable_enterprise_modules)
		
		selected = response['selected_rows']
		if selected != []:
			st.table(selected)
		
	if func_escolhida == 'Visualizar Troubleshoot':
		st.subheader('Visualizar Troubleshoot')
		df_troubleshoot = load_forms('troubleshoot')
		col1, col2, _equipamento, _nome = st.beta_columns([2,2,3,9])
		inicio_filtro = col1.date_input("Início (ano/mês/dia)", datetime(2021, 7, 1))
		fim_filtro = col2.date_input("Fim (ano/mês/dia)")
		df_troubleshootfiltrado = (df_troubleshoot[(df_troubleshoot['Data'] >= inicio_filtro) & (df_troubleshoot['Data'] <= fim_filtro)]) 

		# Gera lista dos responsáveis
		list_eq = list(df_troubleshootfiltrado['Equipamento'].drop_duplicates())
		list_eq.append('todos') 
		equip = _equipamento.selectbox("Selecione o equipamento", list_eq, list_eq.index('todos'))
		
		# Inicia o filtro com todos
		if equip == 'todos':
			pass
		elif equip is not None and (str(equip) != 'nan'):
			df_troubleshootfiltrado = df_troubleshootfiltrado[df_troubleshootfiltrado['Equipamento'] == equip]

		# Gera lista dos gestor	
		list_nome = list(df_troubleshootfiltrado['Nome'].drop_duplicates())
		list_nome.append('todos')  
		colaborador = _nome.selectbox("Selecione o colaborador", list_nome, list_nome.index('todos'))
		
		# Inicia o filtro com todos
		if colaborador == 'todos':
			pass
		elif colaborador is not None and (str(colaborador) != 'nan'):
			df_troubleshootfiltrado = df_troubleshootfiltrado[df_troubleshootfiltrado['Nome'] == colaborador]		
		
		gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules = config_grid(df_troubleshoot, False)
		response = AgGrid(
			    df_troubleshootfiltrado, 
			    gridOptions=gridOptions,
			    height=grid_height, 
			    width='100%',
			    data_return_mode=return_mode_value, 
			    update_mode=update_mode_value,
			    fit_columns_on_grid_load=fit_columns_on_grid_load,
			    allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
			    enable_enterprise_modules=enable_enterprise_modules)
		
		selected = response['selected_rows']
		if selected != []:
			st.table(selected)
	
	if func_escolhida == 'Suporte Engenharia':
		st.subheader('Suporte da aplicação LID Forms')
		
		# Campo para preenchimento de mensagem
		mensagem_suporte = st.text_input('Preencha o campo abaixo para reportar erros ou sugerir melhorias')
		
		# Campo para email
		email_contato = st.text_input('E-mail para contato (Opcional)')
		
		# Montagem da mensagem
		mensagem = mensagem_suporte + '\n\n' + email_contato
		
		# Envio da mensagem
		enviar_suporte = st.button('Enviar e-mail para suporte')
		if enviar_suporte:
			if mensagem_suporte != '':
				send_email('BRMAI0513@ambev.com.br', 4, '', mensagem, 0)
			else:
				st.error('Preencher a mensagem')
		
		st.subheader('Gestão da aplicação')
		
		# Reseta cache para refazer leitura dos bancos
		reset_db = st.button('Atualizar base de dados')
		if reset_db:
			caching.clear_cache()
			
	if func_escolhida == 'Estatisticas':
		st.subheader('Estatisticas de preenchimento de CIL')
		#st.write('Selecione as datas:')
		
		###############################################
		# CIL diario
		###############################################
		
		# liner diario
		liner_d = df_cil_liner_d.copy()
		liner_d['I2'] = liner_d['I2'].dt.date
		liner_d = liner_d.rename(columns={'I2': 'Datas'})
		liner_d = liner_d.replace({'NOK':0, 'OK':1})
		liner_d['Liner'] = round((liner_d['Q00'] + liner_d['Q01'] + liner_d['Q02'] + liner_d['Q03'] + liner_d['Q04'] + liner_d['Q05'] + liner_d['Q06'] + liner_d['Q07'] + liner_d['Q08'])*100/9, 2)
		liner_d = liner_d.groupby('Datas', group_keys=False).mean()
		liner_d.reset_index(level=0, inplace=True)
		liner_d['Liner'] = round(liner_d['Liner'],2) 
		
		# Shell diario
		shell_d = df_cil_shell_d.copy()
		shell_d['I2'] = shell_d['I2'].dt.date
		shell_d = shell_d.rename(columns={'I2': 'Datas'})
		shell_d.drop_duplicates(subset=['Datas'])
		shell_d = shell_d.replace({'NOK':0, 'OK':1})
		shell_d['Shell'] = round((shell_d['Q00'] + shell_d['Q01'] + shell_d['Q02'] + shell_d['Q03'] + shell_d['Q04'] + shell_d['Q05'] + shell_d['Q06'] + shell_d['Q07'] + shell_d['Q08'] + shell_d['Q09'] + shell_d['Q10'] + shell_d['Q11'] + shell_d['Q12'] + shell_d['Q13'] + shell_d['Q14'] + shell_d['Q15'] + shell_d['Q16'] + shell_d['Q17'] + shell_d['Q18'])*100/19, 2)
		shell_d = shell_d.groupby('Datas', group_keys=False).mean()
		shell_d.reset_index(level=0, inplace=True)
		shell_d['Shell'] = round(shell_d['Shell'],2) 
		
		# autobagger diario
		auto_d = df_cil_auto_d.copy()
		auto_d['I2'] = auto_d['I2'].dt.date
		auto_d = auto_d.rename(columns={'I2': 'Datas'})
		auto_d.drop_duplicates(subset=['Datas'])
		auto_d = auto_d.replace({'NOK':0, 'OK':1})
		auto_d['Autobagger'] = round((auto_d['Q00'] + auto_d['Q01'] + auto_d['Q02'] + auto_d['Q03'] + auto_d['Q04'] + auto_d['Q05'])*100/6, 2)
		auto_d = auto_d.groupby('Datas', group_keys=False).mean()
		auto_d.reset_index(level=0, inplace=True)
		auto_d['Autobagger'] = round(auto_d['Autobagger'],2) 
		
		# conversion diario
		conv_d = df_cil_conv_d.copy()
		conv_d['I2'] = conv_d['I2'].dt.date
		conv_d = conv_d.rename(columns={'I2': 'Datas'})
		conv_d.drop_duplicates(subset=['Datas'])
		conv_d = conv_d.replace({'NOK':0, 'OK':1})
		conv_d['Conversion'] = round((conv_d['Q00'] + conv_d['Q01'] + conv_d['Q02'] + conv_d['Q03'] + conv_d['Q04'] + conv_d['Q05'] + conv_d['Q06'] )*100/7, 2)
		conv_d = conv_d.groupby('Datas', group_keys=False).mean()
		conv_d.reset_index(level=0, inplace=True)
		conv_d['Conversion'] = round(conv_d['Conversion'],2) 
				
		# Balancer diario
		bala_d = df_cil_bala_d.copy()
		bala_d['I2'] = bala_d['I2'].dt.date
		bala_d = bala_d.rename(columns={'I2': 'Datas'})
		bala_d.drop_duplicates(subset=['Datas'])
		bala_d = bala_d.replace({'NOK':0, 'OK':1})
		bala_d['Balancer'] = round((bala_d['Q00'] + bala_d['Q01'] + bala_d['Q02'] )*100/3, 2)
		bala_d = bala_d.groupby('Datas', group_keys=False).mean()
		bala_d.reset_index(level=0, inplace=True)
		bala_d['Balancer'] = round(bala_d['Balancer'],2) 
		
		# filtro para as datas
		col1, col2 = st.beta_columns(2)
		inicio_filtro = col1.date_input("Início (ano/mês/dia)", datetime(2021, 7, 1))
		fim_filtro = col2.date_input("Fim (ano/mês/dia)")
		
		# Cria dataframe vazio para as datas
		cil_diario = pd.DataFrame()
		cil_diario['Datas'] = pd.date_range(start=inicio_filtro, end=fim_filtro)
		cil_diario['Datas'] = cil_diario['Datas'].dt.date
		
		# concatena dataframes
		cil_diario = pd.merge(cil_diario, liner_d[['Datas','Liner']], on='Datas', how='left')
		cil_diario = pd.merge(cil_diario, shell_d[['Datas','Shell']], on='Datas', how='left')
		cil_diario = pd.merge(cil_diario, auto_d[['Datas','Autobagger']], on='Datas', how='left')
		cil_diario = pd.merge(cil_diario, conv_d[['Datas','Conversion']], on='Datas', how='left')
		cil_diario = pd.merge(cil_diario, bala_d[['Datas','Balancer']], on='Datas', how='left')		
		
		# trata dados faltantes
		cil_diario = cil_diario.replace(np.nan, '-', regex=True)
		
		###############################################
		# CIL semanal
		###############################################
		
		cil_semanal = pd.DataFrame()
		cil_semanal['Semana'] = [*range(1, 56, 1)]
		
		# liner semanal
		liner_s = df_cil_liner_s.copy()
		liner_s['Semana'] = liner_s['I2'].dt.strftime('%V')
		liner_s['Semana'] = liner_s['Semana'].astype(int)
		liner_s['Semanas'] = liner_s['Semana']
		liner_s = liner_s.replace({'NOK':0, 'OK':1})
		liner_s['Liner'] = round((liner_s['Q00'] + liner_s['Q01'] + liner_s['Q02'] + liner_s['Q03'] + liner_s['Q04'] + liner_s['Q05'] + liner_s['Q06'] + liner_s['Q07'] + liner_s['Q08'] + liner_s['Q09'] + liner_s['Q10'] + liner_s['Q11'] + liner_s['Q12'] + liner_s['Q13'] + liner_s['Q14'] + liner_s['Q15'] + liner_s['Q16'] + liner_s['Q17'] + liner_s['Q18'] + liner_s['Q19'] + liner_s['Q20'] + liner_s['Q21'] + liner_s['Q22'])*100/23, 2)
		liner_s = liner_s.groupby(['Semanas']).mean()
		
		# shell semanal
		shell_s = df_cil_shell_s.copy()
		shell_s['Semana'] = shell_s['I2'].dt.strftime('%V')
		shell_s['Semana'] = shell_s['Semana'].astype(int)
		shell_s['Semanas'] = shell_s['Semana']
		shell_s = shell_s.replace({'NOK':0, 'OK':1})
		shell_s['Shell'] = round((shell_s['Q00'] + shell_s['Q01'] + shell_s['Q02'] + shell_s['Q03'] + shell_s['Q04'] + shell_s['Q05'] + shell_s['Q06'] + shell_s['Q07'] + shell_s['Q08'] + shell_s['Q09'] + shell_s['Q10'] + shell_s['Q11'] + shell_s['Q12'] + shell_s['Q13'] + shell_s['Q14'] + shell_s['Q15'] + shell_s['Q16'] + shell_s['Q17'] + shell_s['Q18'] + shell_s['Q19'] + shell_s['Q20'])*100/21, 2)
		shell_s = shell_s.groupby(['Semanas']).mean()	
		
		# autobagger semanal
		auto_s = df_cil_auto_s.copy()
		auto_s['Semana'] = auto_s['I2'].dt.strftime('%V')
		auto_s['Semana'] = auto_s['Semana'].astype(int)
		auto_s['Semanas'] = auto_s['Semana']
		auto_s = auto_s.replace({'NOK':0, 'OK':1})
		auto_s['Autobagger'] = round((auto_s['Q00'] + auto_s['Q01'] + auto_s['Q02'] + auto_s['Q03'] + auto_s['Q04'] + auto_s['Q05'])*100/6, 2)
		auto_s = auto_s.groupby(['Semanas']).mean()		
		
		# conversion semanal
		conv_s = df_cil_conv_s.copy()
		conv_s['Semana'] = conv_s['I2'].dt.strftime('%V')
		conv_s['Semana'] = conv_s['Semana'].astype(int)
		conv_s['Semanas'] = conv_s['Semana']
		conv_s = conv_s.replace({'NOK':0, 'OK':1})
		conv_s['Conversion'] = round((conv_s['Q00'] + conv_s['Q01'] + conv_s['Q02'] + conv_s['Q03'] + conv_s['Q04'] + conv_s['Q05'] + conv_s['Q06'] + conv_s['Q07'] + conv_s['Q08'] + conv_s['Q09'] + conv_s['Q10'] + conv_s['Q11'] + conv_s['Q12'] + conv_s['Q13'] + conv_s['Q14'] + conv_s['Q15'] + conv_s['Q16'] + conv_s['Q17'] + conv_s['Q18'] + conv_s['Q19'] + conv_s['Q20'] + conv_s['Q21'] + conv_s['Q22'] + conv_s['Q23'])*100/24, 2)
		conv_s = conv_s.groupby(['Semanas']).mean()	
		
		# balancer semanal
		bala_s = df_cil_bala_s.copy()
		bala_s['Semana'] = bala_s['I2'].dt.strftime('%V')
		bala_s['Semana'] = bala_s['Semana'].astype(int)
		bala_s['Semanas'] = bala_s['Semana']
		bala_s = bala_s.replace({'NOK':0, 'OK':1})
		bala_s['Balancer'] = round((bala_s['Q00'] + bala_s['Q01'] + bala_s['Q02'])*100/3, 2)
		bala_s = bala_s.groupby(['Semanas']).mean()
		
		# concatena dataframes
		cil_semanal = pd.merge(cil_semanal, liner_s[['Semana','Liner']], on='Semana', how='left')
		cil_semanal = pd.merge(cil_semanal, shell_s[['Semana','Shell']], on='Semana', how='left')
		cil_semanal = pd.merge(cil_semanal, auto_s[['Semana','Autobagger']], on='Semana', how='left')
		cil_semanal = pd.merge(cil_semanal, conv_s[['Semana','Conversion']], on='Semana', how='left')
		cil_semanal = pd.merge(cil_semanal, bala_s[['Semana','Balancer']], on='Semana', how='left')
		
		# aplica filtros de datas
		inicio_semana = inicio_filtro.strftime('%V')
		fim_semana = fim_filtro.strftime('%V')
		cil_semanal = cil_semanal[(cil_semanal['Semana'] >= int(inicio_semana)) & (cil_semanal['Semana'] <= int(fim_semana))]
		
		# trata dados faltantes
		cil_semanal = cil_semanal.replace(np.nan, '-', regex=True)
		
		###############################################
		# CIL mensal
		###############################################
		
		cil_mensal = pd.DataFrame()
		cil_mensal['Mes'] = [*range(1, 12, 1)]
		
		# autobagger semanal
		auto_m = df_cil_auto_m.copy()
		auto_m['Mes'] = auto_m['I2'].dt.month
		auto_m['Mes'] = auto_m['Mes'].astype(int)
		auto_m['Meses'] = auto_m['Mes']
		auto_m = auto_m.replace({'NOK':0, 'OK':1})
		auto_m['Autobagger'] = round((auto_m['Q00'] + auto_m['Q01'] + auto_m['Q02'] + auto_m['Q03'] + auto_m['Q04'] + auto_m['Q05'] + auto_m['Q06'] + auto_m['Q07'] + auto_m['Q08'])*100/9, 2)
		auto_m = auto_m.groupby(['Meses']).mean()	
		
		# autobagger semanal
		conv_m = df_cil_conv_m.copy()
		conv_m['Mes'] = conv_m['I2'].dt.month
		conv_m['Mes'] = conv_m['Mes'].astype(int)
		conv_m['Meses'] = conv_m['Mes']
		conv_m = conv_m.replace({'NOK':0, 'OK':1})
		conv_m['Conversion'] = round((conv_m['Q00'] + conv_m['Q01'] + conv_m['Q02'] + conv_m['Q03'] + conv_m['Q04'] + conv_m['Q05'] + conv_m['Q06'] + conv_m['Q07'] + conv_m['Q08'] + conv_m['Q09'] + conv_m['Q10'] + conv_m['Q11'] + conv_m['Q12'] + conv_m['Q13'])*100/14, 2)
		conv_m = conv_m.groupby(['Meses']).mean()
		
		# concatena dataframes
		cil_mensal = pd.merge(cil_mensal, auto_m[['Mes','Autobagger']], on='Mes', how='left')
		cil_mensal = pd.merge(cil_mensal, conv_m[['Mes','Conversion']], on='Mes', how='left')

		# aplica filtros de datas
		inicio_mes = inicio_filtro.month
		fim_mes = fim_filtro.month
		cil_mensal = cil_mensal[(cil_mensal['Mes'] >= int(inicio_mes)) & (cil_mensal['Mes'] <= int(fim_mes))]
		
		# trata dados faltantes
		cil_mensal = cil_mensal.replace(np.nan, '-', regex=True)

		# organizacao das colunas
		col_d, col_s, col_m = st.beta_columns([4,4,2])
		
		with col_d:
			st.subheader('Percentual de CIL diário:')
			# Monta planilha para exibir dados
			gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules = config_grid(cil_diario, True)
			response = AgGrid(
				    cil_diario, 
				    gridOptions=gridOptions,
				    height=grid_height, 
				    width='100%',
				    data_return_mode=return_mode_value, 
				    update_mode=update_mode_value,
				    fit_columns_on_grid_load=fit_columns_on_grid_load,
				    allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
				    enable_enterprise_modules=enable_enterprise_modules)

			selected = response['selected_rows']
			
			if selected != []:
				st.table(selected)
				
		with col_s:
			st.subheader('Percentual de CIL semanal:')
			# Monta planilha para exibir dados
			gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules = config_grid(cil_semanal, True)
			response = AgGrid(
				    cil_semanal, 
				    gridOptions=gridOptions,
				    height=grid_height, 
				    width='100%',
				    data_return_mode=return_mode_value, 
				    update_mode=update_mode_value,
				    fit_columns_on_grid_load=fit_columns_on_grid_load,
				    allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
				    enable_enterprise_modules=enable_enterprise_modules)

			selected = response['selected_rows']
			
		with col_m:
			st.subheader('Percentual de CIL mensal:')
			# Monta planilha para exibir dados
			gridOptions, grid_height, return_mode_value, update_mode_value, fit_columns_on_grid_load, enable_enterprise_modules = config_grid(cil_mensal, True)
			response = AgGrid(
				    cil_mensal, 
				    gridOptions=gridOptions,
				    height=grid_height, 
				    width='100%',
				    data_return_mode=return_mode_value, 
				    update_mode=update_mode_value,
				    fit_columns_on_grid_load=fit_columns_on_grid_load,
				    allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
				    enable_enterprise_modules=enable_enterprise_modules)

			selected = response['selected_rows']
			
		# Criação dos gráficos (5 subplots)
		fig = make_subplots(rows=1, 
			    cols=5,
			    subplot_titles=("CIL por equipamento (diario)", "Distribuição por turno(diario)", "CIL por equipamento (semanal)", "Distribuição por turno(semanal)", "CIL por equipamento (mensal)"),
			    column_widths=[0.2, 0.2, 0.2, 0.2, 0.2]
			   )
		
		########### diario ##############
		# gera dados sobre a quantidade de cil de cada maquina diario
		aux_d = cil_diario
		grafico_d = pd.DataFrame()
		grafico_d['Liner'] = np.where(aux_d['Liner']=='-', 0, 1) 
		grafico_d['Shell'] = np.where(aux_d['Shell']=='-', 0, 1) 
		grafico_d['Autobagger'] = np.where(aux_d['Autobagger']=='-', 0, 1) 
		grafico_d['Conversion'] = np.where(aux_d['Conversion']=='-', 0, 1) 
		grafico_d['Balancer'] = np.where(aux_d['Balancer']=='-', 0, 1) 
		grafico_d['Esperado'] = 1

		# quantidade de cil por turno diario
		turnos_d = df_cil_liner_d['I1']
		turnos_d = turnos_d.append(df_cil_shell_d['I1'])
		turnos_d = turnos_d.append(df_cil_auto_d['I1'])
		turnos_d = turnos_d.append(df_cil_conv_d['I1'])
		turnos_d = turnos_d.append(df_cil_bala_d['I1'])

		########### semanal ##############
		# gera dados sobre a quantidade de cil de cada maquina diario
		aux_s = cil_semanal
		grafico_s = pd.DataFrame()
		grafico_s['Liner'] = np.where(aux_s['Liner']=='-', 0, 1) 
		grafico_s['Shell'] = np.where(aux_s['Shell']=='-', 0, 1) 
		grafico_s['Autobagger'] = np.where(aux_s['Autobagger']=='-', 0, 1) 
		grafico_s['Conversion'] = np.where(aux_s['Conversion']=='-', 0, 1) 
		grafico_s['Balancer'] = np.where(aux_s['Balancer']=='-', 0, 1) 
		grafico_s['Esperado'] = 1

		# quantidade de cil por turno diario
		turnos_s = df_cil_liner_s['I1']
		turnos_s = turnos_s.append(df_cil_shell_s['I1'])
		turnos_s = turnos_s.append(df_cil_auto_s['I1'])
		turnos_s = turnos_s.append(df_cil_conv_s['I1'])
		turnos_s = turnos_s.append(df_cil_bala_s['I1'])
		
		########### mensal ##############
		# gera dados sobre a quantidade de cil de cada maquina diario
		aux_m = cil_mensal
		grafico_m = pd.DataFrame()
		grafico_m['Autobagger'] = np.where(aux_m['Autobagger']=='-', 0, 1) 
		grafico_m['Conversion'] = np.where(aux_m['Conversion']=='-', 0, 1) 
		grafico_m['Esperado'] = 1
		
		# definicao das cores
		colors = ['lightslategray',] * 6
		colors[5] = 'crimson'
		colors_m = ['lightslategray',] * 3
		colors_m[2] = 'crimson'
		
		fig.add_trace(go.Bar(x=['Liner' ,'Shell', 'Autobagger', 'Conversion', 'Balancer', 'Esperado'], y=grafico_d.sum(), marker_color=colors), row=1, col=1)
		fig.add_trace(go.Histogram(x=turnos_d, marker_color=colors), row=1, col=2)
		fig.add_trace(go.Bar(x=['Liner' ,'Shell', 'Autobagger', 'Conversion', 'Balancer', 'Esperado'], y=grafico_s.sum(), marker_color=colors), row=1, col=3)
		fig.add_trace(go.Histogram(x=turnos_s, marker_color=colors), row=1, col=4)
		fig.add_trace(go.Bar(x=['Autobagger', 'Conversion', 'Esperado'], y=grafico_m.sum(),  marker_color=colors_m), row=1, col=5)

		fig.update_layout(height=300, width=1800, showlegend=False)
		st.write(fig)

