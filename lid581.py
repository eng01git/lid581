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
import json
import smtplib
import time
import datetime
import time
from datetime import  date
import base64
from io import BytesIO

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

# Link do arquivo com os dados
DATA_URL = "data.csv"

######################################################################################################
				     #Definição da sidebar
######################################################################################################

fig1s, fig2s, fig3s = st.sidebar.beta_columns([1,2,1])
fig1s.write('')
fig2s.image('latas minas.png', width=150)
fig3s.write('')
st.sidebar.title("LID Forms")
formularios = [
	'Liner diário',
	'Liner semanal',
	'Shell diário',
	'Shell semanal',
	'Autobagger diário',
	'Autobagger semanal',
	'Autobagger Mensal',
	'Conversion diário',
	'Conversion semanal',
	'Conversion mensal',
	'Balacer diário',
	'Balancer semanal',
	'Estatisticas',			# Gráficos com filtros
	'Visualizar formulários',	# Filtros para visualizar os questionários desejeados
	'Suporte Engenharia'
]

func_escolhida = st.sidebar.radio('Selecione o formulário de saída', formularios, index=0)

######################################################################################################
                               #Função para leitura do banco (Firebase)
######################################################################################################
# Efetua a leitura de todos os documentos presentes no banco e passa para um dataframe pandas
# Função para carregar os dados do firebase (utiliza cache para agilizar a aplicação)

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
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.selectbox('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.selectbox('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.selectbox('Item 8:', respostas)
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
		I0, I1, I2 = st.beta_columns([8,3,3])
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
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.selectbox('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.selectbox('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.selectbox('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.selectbox('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.selectbox('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.selectbox('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.selectbox('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.selectbox('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.selectbox('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.selectbox('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.selectbox('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.selectbox('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.selectbox('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		dic['Q19'] = Q19.selectbox('Item 19:', respostas)
		dic['C19'] = C19.text_input('Comentário item 19:', "")
		dic['Q20'] = Q20.selectbox('Item 20:', respostas)
		dic['C20'] = C20.text_input('Comentário item 20:', "")
		dic['Q21'] = Q21.selectbox('Item 21:', respostas)
		dic['C21'] = C21.text_input('Comentário item 21:', "")
		dic['Q22'] = Q22.selectbox('Item 22:', respostas)
		dic['C22'] = C22.text_input('Comentário item 22:', "")
		
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
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		T03.info('Cilindro do quick lifit: 1. Verificar quanto a vazamentos de óleo.')
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.selectbox('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.selectbox('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.selectbox('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.selectbox('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.selectbox('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.selectbox('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.selectbox('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.selectbox('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.selectbox('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.selectbox('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.selectbox('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.selectbox('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.selectbox('Item 18:', respostas)
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
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.selectbox('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.selectbox('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.selectbox('Item 8:', respostas)
		dic['C08'] = C08.text_input('Comentário item 8:', "")
		dic['Q09'] = Q09.selectbox('Item 9:', respostas)
		dic['C09'] = C09.text_input('Comentário item 9:', "")
		dic['Q10'] = Q10.selectbox('Item 10:', respostas)
		dic['C10'] = C10.text_input('Comentário item 10:', "")
		dic['Q11'] = Q11.selectbox('Item 11:', respostas)
		dic['C11'] = C11.text_input('Comentário item 11:', "")
		dic['Q12'] = Q12.selectbox('Item 12:', respostas)
		dic['C12'] = C12.text_input('Comentário item 12:', "")
		dic['Q13'] = Q13.selectbox('Item 13:', respostas)
		dic['C13'] = C13.text_input('Comentário item 13:', "")
		dic['Q14'] = Q14.selectbox('Item 14:', respostas)
		dic['C14'] = C14.text_input('Comentário item 14:', "")
		dic['Q15'] = Q15.selectbox('Item 15:', respostas)
		dic['C15'] = C15.text_input('Comentário item 15:', "")
		dic['Q16'] = Q16.selectbox('Item 16:', respostas)
		dic['C16'] = C16.text_input('Comentário item 16:', "")
		dic['Q17'] = Q17.selectbox('Item 17:', respostas)
		dic['C17'] = C17.text_input('Comentário item 17:', "")
		dic['Q18'] = Q18.selectbox('Item 18:', respostas)
		dic['C18'] = C18.text_input('Comentário item 18:', "")
		dic['Q19'] = Q19.selectbox('Item 19:', respostas)
		dic['C19'] = C19.text_input('Comentário item 19:', "")
		dic['Q20'] = Q20.selectbox('Item 20:', respostas)
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
		I0, I1, I2 = st.beta_columns([8,3,3])
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])
		T03, Q03, C03 = st.beta_columns([3,1,3])
		T04, Q04, C04 = st.beta_columns([3,1,3])
		T05, Q05, C05 = st.beta_columns([3,1,3])
		
		# Texto das questões
		T00.info('Recolhimento de tampas (Autobagger Área do piso no entorno do equipamento, é área do piso interior do equipamento.): 1- Limpeza utilizando uma vassoura, pá e soprador de ar. Com as mãos, retire as tampas que ficaram presas dentro dos trays do Auto Bagger. Utilize o soprador para retirar as tampas do chão em parte de difícil acesso e logo após deve-se varrer e recolher as tampas utilizando a pá, e colocar no balde de scrap.')
		T01.info('Proteções e parte externa das máquinas (Área do pallettizer / autobagger): 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe alguma anomalia.')
		T02.info('Limpeza dos filtros (entrada e saída) - Autobagger e Palettizer Unidade de conservação (verificar a numeração em campo): 1- Limpeza de ambos os filtros (filtro de partículas e filtro coalescente) utilizando fluxo de ar e drenagem. Deve-se observar se os mesmos estão saturados, se caso estiver, devem ser trocados..')
		T03.info('Temperatura do aquecedor (Autobagger Sistema de fechamento do Bag): 1- Realizar o check diário da correta especificação de temperatura.')
		T04.info('Limpeza de todas as portas e teto da área do Autobagger. (Autobagger): 1- Limpar com pano  umedecido e álcool isopropílico.')
		T05.info('Limpeza de todas as portas e teto da área do Autobagger: 1- Limpar com pano  umedecido e álcool isopropílico.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
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
			doc_ref = db.collection("Autobagger_diario").document(val_documento)
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

def Autobagger_semanal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
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
			doc_ref = db.collection("Autobagger_semanal").document(val_documento)
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

def Autobagger_mensal():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
		dic['C05'] = C05.text_input('Comentário item 5:', "")
		dic['Q06'] = Q06.selectbox('Item 6:', respostas)
		dic['C06'] = C06.text_input('Comentário item 6:', "")
		dic['Q07'] = Q07.selectbox('Item 7:', respostas)
		dic['C07'] = C07.text_input('Comentário item 7:', "")
		dic['Q08'] = Q08.selectbox('Item 8:', respostas)
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
			doc_ref = db.collection("Autobagger_mensal").document(val_documento)
			doc_ref.set(new_d)
			st.success('Formulário armazenado com sucesso!')
		except:
			st.error('Falha ao armazenar formulário, tente novamente ou entre em contato com suporte!')

		
def Autobagger_mensal_proc():
	with st.beta_expander('Pontos'):
		st.image('autobagger_mensal/Pontos mensal autobagger.jpg')

	with st.beta_expander('Procedimentos folha 1'):
		st.image('autobagger_mensal/folha1.jpg')
				
	with st.beta_expander('Procedimentos folha 2'):
		st.image('autobagger_mensal/folha2.jpg')
				
	with st.beta_expander('Procedimentos folha 3'):
		st.image('autobagger_mensal/folha3.jpg')
				
	with st.beta_expander('Procedimentos folha 4'):
		st.image('autobagger_mensal/folha4.jpg')

		
def balancer_diario():
	
	with st.form('Form'):
    
		# Define a organização das colunas
		I0, I1, I2 = st.beta_columns([8,3,3])
		T00, Q00, C00 = st.beta_columns([3,1,3])
		T01, Q01, C01 = st.beta_columns([3,1,3])
		T02, Q02, C02 = st.beta_columns([3,1,3])

		# Texto das questões
		T00.info('Proteções e partes externas da máquina: 1- Limpeza com pano umedecido em álcool isopropílico, nas proteções externas da máquina. Inspecionar toda a área se existe  alguma anomalia.')
		T01.info('Piso do interior da máquina: 1- Realizar a limpeza dos pontos de difícil acesso do piso e parte inferior da máquina com um soprador. Após soprar todas as tampas, utilizar vassoura e pá para recolher  e descarta-las em local adequado.')
		T02.info('Piso exterior da máquina: 1- Executar limpeza nos pontos externos de difícil acesso na parte inferior da máquina da máquina.')
			
		respostas = ['NOK', 'OK']

		# Questões
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
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
		st.image('balancer_diario/Pontos diario balancer.jpg')

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
		I0, I1, I2 = st.beta_columns([8,3,3])
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
		dic['I0' ] = I0.selectbox('Nome do colaborador', nomes) #definir nomes
		dic['I1' ] = I1.selectbox('Selecione o turno', turnos )
		dic['I2' ] = I2.date_input('Selecione a data')
		dic['Q00'] = Q00.selectbox('Item 0: ', respostas)
		dic['C00'] = C00.text_input('Comentário item 0:', "")
		dic['Q01'] = Q01.selectbox('Item 1:', respostas)
		dic['C01'] = C01.text_input('Comentário item 1:', "")
		dic['Q02'] = Q02.selectbox('Item 2:', respostas)
		dic['C02'] = C02.text_input('Comentário item 2:', "")
		dic['Q03'] = Q03.selectbox('Item 3:', respostas)
		dic['C03'] = C03.text_input('Comentário item 3:', "")
		dic['Q04'] = Q04.selectbox('Item 4:', respostas)
		dic['C04'] = C04.text_input('Comentário item 4:', "")
		dic['Q05'] = Q05.selectbox('Item 5:', respostas)
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
		
######################################################################################################
                                           #Main
######################################################################################################

if __name__ == '__main__':
	# Carrega dados dos colaboradores
	usuarios = load_users()


	# Constantes
	turnos = ['Turno A', 'Turno B', 'Turno C']
	nomes = list(usuarios.iloc[:,2])

	# Imagem
	col1_, col2_, col3_ = st.beta_columns([1,1,1])
	col1_.write('')
	col2_.image('Ambev.jpeg', width=250)
	col3_.write('')

	# Lista vazia para input dos dados do formulário
	dic = {} #dicionario

	##################################################################################################
	#			Definiçào das páginas
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
		
	if func_escolhida == 'Autobagger Mensal':
		st.subheader('Autobagger Mensal')
		proc_LS = st.checkbox('Deseja visualizar os procedimentos?')	
		if proc_LS:
			Autobagger_mensal_proc()
		Autobagger_mensal()
		
	if func_escolhida == 'Conversion diário':
		st.subheader('Conversion diário')
		
	if func_escolhida == 'Conversion semanal':
		st.subheader('Conversion semanal')
		
	if func_escolhida == 'Conversion mensal':
		st.subheader('Conversion mensal')
		
	if func_escolhida == 'Balacer diário':
		st.subheader('Balacer diário')
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
		
	if func_escolhida == 'Visualizar formulários':
		st.subheader('Visualizar formulários')
				
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
		st.subheader('Estatisticas')
		import streamlit.components.v1 as components
		cordax_otions = [
			'tela1',
			'tela2',
		]

		lid_cordax = st.sidebar.radio('Selecione a tela', cordax_otions, index=0)

		
		file_ = open("Untitled.png", "rb")
		contents = file_.read()
		data_url = base64.b64encode(contents).decode("utf-8")
		file_.close()

		#file_ = open("index.html", "r")
		#index_html = file_.read()
		#index_html = base64.b64encode(contents).decode("utf-8")
		#file_.close()
		
		if lid_cordax == 'tela1':
			htmlfile = open('teste.html', 'r', encoding='utf-8')
			source = htmlfile.read()

			with st.form('form1'):
				t1, t2, t3 = st.beta_columns([2,10,2])
				t1.write('SPACER LOWER CAP')
				dic['D00'] = t1.number_input('A:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f', key='SLC A')
				dic['D01'] = t1.number_input('A:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f', key='SLC B')
				dic['D02'] = t1.number_input('C:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f', key='SLC C')
				dic['D03'] = t1.number_input('D:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f', key='SLC D')
				
				val1 = t1.number_input('SLC A:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f')
				
				with t2:
					components.html(source.format(image=data_url, teste=val1), height=1010)
					
				val1 = t3.number_input('asd2 A:')
				val2 = t3.number_input('asd2 B:')
				val3 = t3.number_input('asd2 C:')
				
				i01, i02, sub = st.beta_columns([8,1,1])
				dic['I01'] = i01.selectbox('Nome do colaborador:', nomes) 
				dic['I02'] = i02.date_input('Selecione a data')
				submit = sub.form_submit_button('Alterar valores')
		
		if lid_cordax == 'tela2':
			htmlfile = open('teste2.html', 'r', encoding='utf-8')
			source = htmlfile.read()

			with st.form('form2'):
				t1, t2, t3 = st.beta_columns([2,10,2])
				val1 = t1.number_input('asd A:', min_value=0.00010, max_value=0.1001, step=0.001, format='%f')
				with t2:
					components.html(source.format(image=data_url, teste=val1), height=950)
					#components.html(source)
					#st.write('<iframe src="teste.html" width="1000" height="1000"></iframe>', unsafe_allow_html=True)
				val1 = t3.number_input('asd2 A:')	
				submit = t1.form_submit_button('Alterar valores')


