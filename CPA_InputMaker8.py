# -*- coding: utf-8 -*-
"""
Created on 05.07.2024

@author: Oleksandr Shendryk

UNIVERSITY OF ALBERTA
College of Health Sciences
Faculty of Medicine and Dentistry
Department of Laboratory Medicine and Pathology
Division of Analytical and Environmental Toxicology

This program is designed to automatically convert images and their data from IDEAS into a format that can be opened in CellProfiler Analyst.
"""

#importing libraries
import sqlite3
import re
import os
from tkinter import filedialog
import tkinter as tk
import pandas as pd
from datetime import datetime
import numpy as np

#declaring the main window
root = tk.Tk()
root.title("CPA_InputMaker8")
root.state('zoomed')

#variables for image properties
Image_x_loc_Var = tk.StringVar()
Image_x_loc_Var.set('2.5')
Image_y_loc_Var = tk.StringVar()
Image_y_loc_Var.set('14')
Image_Height_Var = tk.StringVar()
Image_Height_Var.set('50')
Image_Width_Var = tk.StringVar()
Image_Width_Var.set('50')
Image_Format_Var = tk.StringVar()
Image_Format_Var.set('.ome.tif')
Filter_IntVar = tk.IntVar()
Filter_IntVar.set(1)
Float32_IntVar = tk.IntVar()
Float32_IntVar.set(1)

#custom exeption class
class MyException(Exception):
    pass

"""
Adds information about images fromn folderAddress folder to dbName database 
Also adds mesurments from txtName file
"""
def per_image(folderAddress,txtName,dbName):
    global Image_Height_Var
    global Image_Width_Var
    global Image_Format_Var
    global Filter_IntVar
    global Float32_IntVar
    
    print(txtName.split('/')[-1].split('.')[0]+' Entered images_to_db ' + str(datetime.now()))
    print("Read txt file start")
    txtDf = pd.read_table(txtName, delimiter="\t", skiprows=1,index_col='Object Number')
    print("Read txt file end")
    
    print("txt Column identification start")
    if 'Object Number.1' in txtDf: #delete dublicated Object Number
        txtDf.drop('Object Number.1', axis=1, inplace=True)
    columnNamesList = re.sub(r"\s", "_", '/'.join(txtDf.columns.tolist())).split('/') #change space to _
    txtDf.columns = columnNamesList #rename columns in the dataframe
    print("txt Column identification end")
    
    print("Read image list start")
    images = os.listdir(folderAddress)#get list of the folders files
    images = np.array(list(filter(lambda x: Image_Format_Var.get() in x, images)))
    print("Read image list end")
    
    print("picture Column identification start")
    imageColumns={}
    firstImageNumber=images[0].split('_')[0]
    for image in images:
        if firstImageNumber in image:
            channal = image.split('_Ch')[1].split('.')[0]#channal number
            imageColumns["Image_FileName_Ch" + channal] = {}
            imageColumns["Image_PathName_Ch" + channal] = {}
            imageColumns["Image_Height_Ch" + channal] = {}
            imageColumns["Image_Width_Ch" + channal] = {}
        else:
            break
    print("picture Column identification end")
    
    
    txtNameShort=txtName.split('/')[-1].split('.')[0]
    Image_Height = Image_Height_Var.get()
    Image_Width = Image_Width_Var.get()
    for image in images:
        print(str(datetime.now()) + ' in per_image: reading step ' + (image + ' from ' + txtNameShort))
        ch=image.split('_Ch')[1].split('.')[0]#channal number
        RealNumber=image.split('_')[0]
        imageColumns["Image_FileName_Ch" + ch][RealNumber] = image
        imageColumns["Image_PathName_Ch" + ch][RealNumber] = folderAddress
        imageColumns["Image_Height_Ch" + ch][RealNumber] = Image_Height
        imageColumns["Image_Width_Ch" + ch][RealNumber] = Image_Width
    
    Per_Image = []
    Per_Image.append("CREATE TABLE IF NOT EXISTS Per_Image(ImageNumber INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, RealNumber Text UNIQUE, ")
    for column in columnNamesList:
        Per_Image.append(column + " FLOAT, ")
    for column in imageColumns:
        if ("FileName" in column) or ("PathName" in column):
            Per_Image.append(column + " TEXT, ")
        else:
            Per_Image.append(column + " INT, ")
        
    Per_Image_Statement = ''.join(Per_Image)
    Per_Image_Statement = Per_Image_Statement[:-2]+')'
    
    conn = sqlite3.connect(dbName)#open database
    conn.execute(Per_Image_Statement)
    
    insert_Per_Image = []
    insert_Per_Image.append("INSERT OR IGNORE INTO Per_Image(RealNumber,")#entering column names
    for column in columnNamesList:
        insert_Per_Image.append(column + ",")
    for column in imageColumns:
        insert_Per_Image.append(column + ",")
    insert_Per_Image_Statement = ''.join(insert_Per_Image)
    insert_Per_Image_Statement = insert_Per_Image_Statement[:-1] + ') Values('

    AreaColumnsList = list(filter(lambda x: "Area" in x, columnNamesList))
    if Filter_IntVar.get():
        filterBool = True
    else:
        filterBool = False
    
    if Float32_IntVar.get():
        float32Bool = True
    else:
        float32Bool = False
    
    cur = conn.cursor()
    for index, row in txtDf.iterrows():#entering values
        insert_Per_Image = []
        RealNumber = str(index)
        print(str(datetime.now()) +' in per_image: writing step ' + txtNameShort + "_" + RealNumber)
        
        try:
            if filterBool:#skip 0 area
                for column in AreaColumnsList:
                    value = str(row[column])
                    if (value == '0.0') or (value == 'nan'):
                        print("Area skip")
                        raise MyException("Area skip")
        except:
            continue

        insert_Per_Image.append("'"+ txtNameShort + "_" + RealNumber + "'")
        
        for column in columnNamesList:
            value = str(row[column])
            if value == 'nan':
                value = '0'
            if 'e' in value:
                value = value.split('e')[0]
            if float32Bool:
                    value = str(np.float32(value))
            insert_Per_Image.append(',' + value)
        for column in imageColumns:
            if ("FileName" in column) or ("PathName" in column):
                insert_Per_Image.append(",'"+str(imageColumns[column][RealNumber]) + "'")
            else:
                insert_Per_Image.append(","+str(imageColumns[column][RealNumber]))
        insert_Per_Image.append(')')
        insert_Per_Image_Statement2 = insert_Per_Image_Statement + ''.join(insert_Per_Image)
        cur.execute(insert_Per_Image_Statement2)
        print('Added to the cursor')
        
    print('Writing to the database start')
    conn.commit()
    print('Writing to the database end')
    conn.close()#close database

"""
Creates or edits a csv file with a training set, adds a new class.
dbName - database address, txtName - txt file with data about class address
"""
def trainingSet(dbName, txtName):
    global Image_x_loc_Var
    global Image_y_loc_Var
    
    txtNameShort = txtName.split('/')[-1].split('.')[0]
    
    print(txtNameShort + ' in trainingSet ' + str(datetime.now()))
    
    conn = sqlite3.connect(dbName)#open database
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Per_Image)")
    columnsTuple=cur.fetchall()
    columnsList = [column[1] for column in columnsTuple]#creating list of columns
    columnsList = list(filter(lambda x: ('Image_FileName_' not in x) and ('Image_PathName_' not in x), columnsList))
    
    selectData_list=[]
    selectData_list.append('SELECT ')
    for column in columnsList:
        selectData_list.append(column+',')
    selectData=''.join(selectData_list)[:-1]
    selectData_list=[]
    selectData_list.append(" FROM Per_Image WHERE RealNumber LIKE '" + txtNameShort + '%\'')
    selectData = selectData + ''.join(selectData_list)
    trainingSetDF = pd.read_sql_query(selectData, conn, index_col='ImageNumber')
    
    ObjectNumber = []
    Class = []
    Image_x_loc = []
    Image_y_loc = []
    x_loc = Image_x_loc_Var.get()
    y_loc = Image_y_loc_Var.get()
    for i in range(len(trainingSetDF.index)):
        ObjectNumber.append('1')
        Class.append(txtNameShort)
        Image_x_loc.append(x_loc)
        Image_y_loc.append(y_loc)
        
    trainingSetDF.insert(0, "ObjectNumber", ObjectNumber, True)
    trainingSetDF.insert(1, "Class", Class, True)
    trainingSetDF.insert(2, "Image_x_loc", Image_x_loc, True)
    trainingSetDF.insert(3, "Image_y_loc", Image_y_loc, True)
    
    dbAddress=dbName[:-(len(dbName.split('/')[-1])+1)]
    directory = os.listdir(dbAddress)
    if dbName.split('/')[-1].split('.')[0] + '_TrainingSet.csv' in directory:
        checkDF = pd.read_csv(dbName[:-3] + '_TrainingSet.csv')
        if txtName.split('/')[-1].split('.')[0] not in list(checkDF['Class']):
            trainingSetDF.to_csv(dbName[:-3] + '_TrainingSet.csv', header = False, mode = 'a')
    else:
        trainingSetDF.to_csv(dbName[:-3] + '_TrainingSet.csv')
    
    
    
    conn.close()#close database

"""
Creates .properties file for dbName database
"""
def properties(dbName):
    
    print('In properties ' + str(datetime.now()))
    
    conn = sqlite3.connect(dbName)#open database
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Per_Image)")
    columnsTuple=cur.fetchall()
    channalNumbers=[]#list of channel numbers
    for column in columnsTuple:
        if 'Image_FileName_Ch' in column[1]:
            channalNumbers.append(column[1].split("_Ch")[1])
    
    prpText = '''db_type         = sqlite
db_sqlite_file  = ''' + dbName + '''
image_table   = Per_Image
object_table  = Per_Object
image_id      = ImageNumber
object_id     = ObjectNumber
plate_id      = 
well_id       = 
series_id     = 
group_id      = 
timepoint_id  = 
cell_x_loc    = Raw_Centroid_X
cell_y_loc    = Raw_Centroid_Y
cell_z_loc    = 
image_path_cols = '''
    for ch in channalNumbers:
        prpText = prpText + "Image_PathName_Ch" + ch +','
    prpText = prpText[:-1] + '''
image_file_cols = '''
    for ch in channalNumbers:
        prpText = prpText + "Image_FileName_Ch" + ch +','
    prpText = prpText[:-1] + '''
image_thumbnail_cols = 
image_names = '''
    for ch in channalNumbers:
        prpText = prpText + "Ch" + ch +','
    prpText = prpText[:-1] + '''
image_channel_colors = '''
    colors = ['green', 'blue', 'red', 'magenta', 'cyan', 'yellow', 'gray']
    i=0
    for ch in channalNumbers:
        prpText = prpText + colors[i] + ','
        i=i+1
        if i == 7:
            i=0
    prpText = prpText[:-1] + '''
channels_per_image  = '''
    for ch in channalNumbers:
        prpText = prpText + '1,'
    prpText = prpText[:-1] + '''
image_channel_blend_modes =
image_url_prepend =
object_name  =  cell, cells,
plate_type  =
classifier_ignore_columns  =  ImageNumber,ObjectNumber,RealNumber
image_tile_size   =  50
image_size =
classification_type  = image
training_set  = ''' + dbName[:-3] + '_TrainingSet.csv' + '''
area_scoring_column =
class_table  = Class
check_tables = no
force_bioformats = no
use_legacy_fetcher = no
process_3D = False'''
    
    prpFile = open(dbName[:-2] + "properties", 'w')#open properties file for writing
    prpFile.write(prpText)# write into properties file
    prpFile.close()
    conn.close()#close database   

#block with GUI (interface)

#creating Scrollbar
mainFrame=tk.Frame(root)
mainFrame.pack(fill='both', expand=1)
canvas=tk.Canvas(mainFrame)
canvas.pack(side='left', fill='both', expand=1)
scroll= tk.Scrollbar(mainFrame, orient='vertical', command=canvas.yview)
scroll.pack(side='right', fill='y')
canvas.configure(yscrollcommand=scroll.set)
canvas.bind('<Configure>',lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvasFrame=tk.Frame(canvas)
canvas.create_window((0,0),window=canvasFrame, anchor="nw")

#database selection
DbAdressVar = tk.StringVar()
DbAdressVar.set('')
DbEntry = tk.Entry(canvasFrame, textvariable = DbAdressVar, width=75)
DbEntry.grid(row=0,column=0)

def selectDatabase():
    DbAdressVar.set(filedialog.asksaveasfilename(filetypes = [('SQLite database files', '*.db')],defaultextension=['SQLite database files', '*.db']))
DbButton = tk.Button(canvasFrame,text = 'Select Database', command = lambda: selectDatabase())
DbButton.grid(row=0,column=1)

#folders and txt selection 
def selectFolder(i):
    folderVars[i].set(filedialog.askdirectory())
def selectTXT(i):
    txtVars[i].set(filedialog.askopenfilename(filetypes =[('Text Documents', '*.txt')]))
    
#for image folders
folderVars = []
folderEntries = []
folderButtons = []
#for txt files
txtVars = []
txtEntries = []
txtButtons = []
#for training set
trainCheckbuttons = []
trainInt = []

folderNum = -1
def addFolder():
    global folderNum
    
    folderNum = folderNum + 1
    folderNumCopy = folderNum
    #create widgets
    folderVars.append(tk.StringVar())
    folderEntries.append(tk.Entry(canvasFrame,textvariable = folderVars[folderNumCopy], width = 75))
    folderButtons.append(tk.Button(canvasFrame,text = 'Select folder '+str(folderNumCopy + 1) + ' address', command = lambda: selectFolder(folderNumCopy)))
    
    txtVars.append(tk.StringVar())
    txtEntries.append(tk.Entry(canvasFrame,textvariable = txtVars[folderNumCopy], width = 75))
    txtButtons.append(tk.Button(canvasFrame,text = 'Select txt '+str(folderNumCopy+1)+' address', command = lambda: selectTXT(folderNumCopy)))
    
    trainInt.append(tk.IntVar())
    trainCheckbuttons.append(tk.Checkbutton(canvasFrame, text="Training Set", variable=trainInt[folderNumCopy],onvalue = 1, offvalue = 0))
    
    #place widgets
    folderVars[folderNumCopy].set('')
    folderEntries[folderNumCopy].grid(row = folderNumCopy+1,column = 0)
    folderButtons[folderNumCopy].grid(row = folderNumCopy+1,column = 1)
    
    txtVars[folderNumCopy].set('')
    txtEntries[folderNumCopy].grid(row = folderNumCopy + 1,column = 2)
    txtButtons[folderNumCopy].grid(row = folderNumCopy + 1,column = 3)
    
    trainInt[folderNumCopy].set(0)
    trainCheckbuttons[folderNumCopy].grid(row=folderNumCopy+1,column=4)
    
    AddFolderButton.grid(row=folderNumCopy+2,column=1)   
    #update scrollbar
    global canvas
    canvas.update_idletasks()
    canvas.config(scrollregion=canvasFrame.bbox())
    
    
#Add folder Button
AddFolderButton = tk.Button(canvasFrame,text = 'Add folder', command = lambda: addFolder())
AddFolderButton.grid(row=1,column=1)

#working with data in the folders and files
def addData():
    global folderNum
    startTime = str(datetime.now())
    print('Start ' + startTime)
    try:
        if '/' in DbAdressVar.get():
            if folderNum > -1:
                for i in range(folderNum+1):
                    if '/' in folderVars[i].get():
                        if '/' in txtVars[i].get():
                            per_image(folderVars[i].get(), txtVars[i].get(), DbAdressVar.get())
                            if trainInt[i].get() == 1:
                                trainingSet(DbAdressVar.get(),txtVars[i].get())
                properties(DbAdressVar.get())
                
                EndTime = str(datetime.now())
                print('Successful end ' + EndTime)
                successRoot = tk.Tk()  # success message window
                successRoot.title('Success')
                successRoot.geometry("300x100")
                successLabel = tk.Label(successRoot, text="""Success
Start time: """ + startTime+ """
End time: """ + EndTime, justify='center').pack()
                successButton = tk.Button(
                    successRoot, text='Ok', command=lambda: successRoot.destroy()).pack()
                successRoot.mainloop()
        else:
            raise MyException("database path is not a path")
        
    except Exception as e:
        EndTime = str(datetime.now())
        print('Error: ' + str(e) + ' ' + EndTime)
        errorRoot=tk.Tk()#error message window
        errorRoot.title("CPA_InputMaker Error")
        errorRoot.geometry("1000x100")
        errorLabel=tk.Label(errorRoot, text='Error: ' + str(e) + """
Start time: """ + startTime+ """
End time: """ + EndTime, justify='center')
        errorLabel.pack()
        errorRoot.mainloop()

ConvertButton = tk.Button(canvasFrame,text = 'Add Data', command = lambda: addData())
ConvertButton.grid(row=0,column=2, sticky="nw")

#menu
rootMenu= tk.Menu(root)
root.config(menu=rootMenu)

#settings window
def open_settings():
    settingsRoot=tk.Toplevel()
    settingsRoot.title("Settings")

    global Image_x_loc_Var
    global Image_y_loc_Var
    global Image_Height_Var
    global Image_Width_Var
    global Image_Format_Var
    global Filter_IntVar
    global Float32_IntVar

    infoLabel = tk.Label(settingsRoot,text = 'Image options. May affect how images are displayed in CellProfiler Analyst.')
    infoLabel.grid(row=0,column=0,columnspan=2)

    Image_x_loc_Label = tk.Label(settingsRoot,text = 'Image_x_loc (Default 2.5)')
    Image_y_loc_Label = tk.Label(settingsRoot,text = 'Image_y_loc (Default 14)')
    Image_Height_Label = tk.Label(settingsRoot,text = 'Image_Height (Default 50)')
    Image_Width_Label = tk.Label(settingsRoot,text = 'Image_Width (Default 50)')
    Image_Format_Label = tk.Label(settingsRoot,text = 'Image_Format (Default .ome.tif)')
    Filter_Checkbutton = tk.Checkbutton(settingsRoot, text="Filter by Area (Default On)", variable=Filter_IntVar,onvalue = 1, offvalue = 0)
    Float32_Label = tk.Label(settingsRoot,text = 'Database options')
    Float32_Checkbutton = tk.Checkbutton(settingsRoot, text="Convert all float values ​​to float32 (Default On)", variable=Float32_IntVar,onvalue = 1, offvalue = 0)

    Image_x_loc_Label.grid(row=1,column=0, sticky="w")
    Image_y_loc_Label.grid(row=2,column=0, sticky="w")
    Image_Height_Label.grid(row=3,column=0, sticky="w")
    Image_Width_Label.grid(row=4,column=0, sticky="w")
    Image_Format_Label.grid(row=5,column=0, sticky="w")
    Filter_Checkbutton.grid(row=6,column=0,columnspan=2,sticky="w")
    Float32_Label.grid(row=7,column=0,columnspan=2)
    Float32_Checkbutton.grid(row=8,column=0,columnspan=2,sticky="w")

    Image_x_loc_Entry = tk.Entry(settingsRoot, textvariable=Image_x_loc_Var)
    Image_y_loc_Entry = tk.Entry(settingsRoot, textvariable=Image_y_loc_Var)
    Image_Height_Entry = tk.Entry(settingsRoot, textvariable=Image_Height_Var)
    Image_Width_Entry = tk.Entry(settingsRoot, textvariable=Image_Width_Var)
    Image_Format_Entry = tk.Entry(settingsRoot, textvariable=Image_Format_Var)

    Image_x_loc_Entry.grid(row=1,column=1)
    Image_y_loc_Entry.grid(row=2,column=1)
    Image_Height_Entry.grid(row=3,column=1)
    Image_Width_Entry.grid(row=4,column=1)
    Image_Format_Entry.grid(row=5,column=1)
    
    settingsRoot.mainloop()
    
rootMenu.add_command(label = 'Settings', command = lambda: open_settings())

#info window
def open_info():
    infoRoot=tk.Tk()
    infoRoot.title("Info")
    
    infoLabel = tk.Label(infoRoot,text = 
'''This program is designed to automatically convert images and their data from IDEAS into a format that can be opened in CellProfiler Analyst.

Select a database by clicking on the Select Database button. The image data will be written to this database. You can select a new one 
or an existing one (then the data will be added to it, it will not be overwritten).

Click the Add folder button to make the field appear for selecting a folder with images and a .txt file from IDEAS. You can select several folders
and .txt files at the same time, they will be added to the database in order from the top to the bottom. Don't worry if you have added too many 
fields for folders, empty fields will be ignored.

Click the Training Set checkbox to add the data to the training set. Whatever you name the .txt file with the data will be the name of the class 
in CellProfiler Analyst. Use only one .txt file per category. You cannot write a file with the same name twice to the same training set.

Click the Add Data button to add information to the database. If you see a success message, then everything is fine.

You can enable or disable filtering by area in the settings (if enabled, objects with a value of 0 for the column containing Area in the title 
will not be added to the database). In the settings you can also change the type of images the program works with and the characteristics 
of image display in CellProfiler Analyst.

Possible causes of errors:
Make sure that the numbers of all photos are mentioned in the .txt file. Make sure that there are no other files in the photo folder other than 
the photos themselves mentioned in the corresponding .txt file. Name .txt files differently for different folders. Photos must be named in the 
format [object number]_Ch[channel number].[file extension]. Do not use .txt files with the same name to write them to the same database.
If there are spaces in the file or folder path this may cause an error. Do not move the database, folders with photos, or the photos themselves.



Author: Oleksandr Shendryk shendryk@ualberta.ca
UNIVERSITY OF ALBERTA
College of Health Sciences
Faculty of Medicine and Dentistry
Department of Laboratory Medicine and Pathology
Division of Analytical and Environmental Toxicology
05.07.2024''', justify = tk.LEFT).pack()

    infoRoot.mainloop()
    
rootMenu.add_command(label = 'Info', command = lambda: open_info())

root.mainloop()

#per_image("D:/User_Files/Work/UofA/CellProfiler/pictures/sperm/Negative", "D:/User_Files/Work/UofA/CellProfiler/CPA_InputMaker/NoSpermTrainingSet2.txt", "D:/User_Files/Work/UofA/CellProfiler/CPA_InputMaker/test4.db")
