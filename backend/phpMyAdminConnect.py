import pymysql

connection = pymysql.connect(
    host='vh454.timeweb.ru',  
    user='cn071868',  
    password='Lbjybc01',
    database='cn071868_data',      
    port=3306                 
)

try:
    cursor =  connection.cursor()
    cursor.execute("SELECT VERSION();")
    version = cursor.fetchone()
    print("Версия MySQL:", version)
except:
    print('error')
finally:
    connection.close()