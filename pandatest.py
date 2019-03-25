
from pandas import DataFrame

Cars = {'Brand': ['Honda Civic','Toyota Corolla','Ford Focus','Audi A4'],
        'Price': [32000,35000,37000,45000]
        }

df = DataFrame(Cars, columns= ['Brand', 'Price'])
export_excel = df.to_excel (r'C:\Users\alnair.m.guevarra\Desktop\drowsiness detection\export_dataframe.xlsx', index = None, header=True)
print (df)

