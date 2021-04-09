import pyopenpose as op
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # 图像控件
import cv2
from time import strftime
from time import localtime
from time import time
from threading import Thread
from threading import Lock
from pymysql import connect
import numpy as np
from os import getcwd
from os import path

'''长度角度函数'''


def Length(A, B):
    return np.sqrt((Pose[n][A][0] - Pose[n][B][0]) ** 2 + (Pose[n][A][1] - Pose[n][B][1]) ** 2)


def Angle(A, B, C):  # Body 25的三个坐标求角度 求∠B
    a = Length(A, B)
    b = Length(B, C)
    c = Length(A, C)
    return (np.arccos((a ** 2 + b ** 2 - c ** 2) / (2 * a * b))) * 180 / np.pi


'''数据库'''


def connect_db():
    global db, cursor
    try:
        db = connect(host='sh-cynosdbmysql-grp-gwyb0d86.sql.tencentcdb.com', port=20487,
                     user='root', password="CHENliyu5078", db='APP_datas')  # 连接数据库
        cursor = db.cursor()  # 获取游标
        date = str(strftime("%Y-%m-%d_%H:%M:%S", localtime()))
        week = str(strftime("%A", localtime()))
        sql = "INSERT INTO " + week + " (Date) VALUES (%s)"
        cursor.execute(sql, (date,))
        db.commit()
        tk.messagebox.showinfo(title='DATABASE', message='Successfully Connect!')
    except:
        tk.messagebox.showwarning(title='DATABASE', message='Please Try Again!')


def disconnect_db():
    global db
    db.close()
    tk.messagebox.showinfo(title='DATABASE', message='Connection Off!')


'''捕捉视频'''


def video_start():
    global SSF_Wait, SLL_Wait, Pose, n, db, canvas, video_flag, cap, sx, sy, cursor, fill_line, canvas3, V
    '''配置模型'''
    params = dict()  # 创建一个字典
    params["model_folder"] = model  # 修改路径
    params["model_pose"] = "BODY_25"  # 选择pose模型
    params["number_people_max"] = 2  # 最大检测人体数
    params["display"] = 2  # 2D模式

    opWrapper = op.WrapperPython()
    opWrapper.configure(params)  # 导入上述参数
    opWrapper.start()
    '''配置模型'''
    cap = cv2.VideoCapture(0)  # 打开摄像头
    Initial = 0
    video_flag = True
    week = str(strftime("%A", localtime()))
    while video_flag:  # 判断是否开启camera
        SSF_Wait = 5
        SLL_Wait = 2  # 加快video速度
        cap.open(0)
        ret, Frame = cap.read()
        H = round(0.63 * sy)
        W = round(0.906 * sy)
        Frame = cv2.resize(Frame, (W, H))  # 图像尺寸变换
        imageToProcess = cv2.cvtColor(Frame, cv2.COLOR_RGB2BGR)  # RGB转换为BGR
        BGR = imageToProcess

        '''计算关节点'''
        datum = op.Datum()
        datum.cvInputData = imageToProcess
        opWrapper.emplaceAndPop(op.VectorDatum([datum]))

        # print("Body keypoints: \n" + str(datum.poseKeypoints))
        Pose = datum.poseKeypoints  # 关键点存在的地方,若无人像，输出None
        # BGR = datum.cvOutputData  # imageToProcess 已识别后的图像
        '''计算关节点'''

        '''初值'''
        if Initial == 0:  # 赋初值
            '''SSF'''
            n = 0  # 默认user=0
            j = 0
            j1 = 0
            j2 = 0
            j3 = 0  # 4种状态
            SSF = 0  # 计数
            SSF_Angle = 270  # 实际角度
            SSF_Max = 270  # 抬手最大值
            SSF_Time = 0  # 测量间隔
            SSF_Num = 3  # 间隔数
            SSF_Hold = 0  # hold时间
            SSF_Flag = 0  # 计时阀门关闭
            SSF_start = 0  # 开始时间
            SSF_Deviation = 0  # 0.18s角度差值
            SSF_Sum = 0  # 角度差值和
            hip_angle = 90  # hip角度
            helper = 'None'
            string2 = 'None'
            comps = 0  # 补偿角
            SSF_Row = 1  # 第1行开始记录
            '''SLL'''
            i = 0
            i1 = 0
            i2 = 0
            i3 = 0
            SLL = 0
            SLL_Angle = 120  # 默认120为开始lift leg
            SLL_Max = 90
            SLL_Time = 0  # 测量间隔
            SLL_Num = 3  # 间隔数
            SLL_Hold = 0  # hold时间
            SLL_Flag = 0  # 计时阀门关闭
            SLL_start = 0  # 开始时间
            SLL_Deviation = 0  # 0.18s角度差值
            SLL_Sum = 0  # 角度差值和
            SLL_Row = 1  # 第1行开始记录
            SLL_string2 = 'None'
            # 实际角度
            V = 1
            Initial = 1  # 赋值完毕
        '''初值'''

        '''模型测量'''
        if str(Pose) != 'None':

            '''Helper'''
            if Pose.shape[0] == 1:
                n = 0  # Only one person
                helper = 'Yes!'
            else:
                if Pose[1][8][2] != 0 and Pose[1][9][2] != 0 and Pose[1][12][2] != 0:
                    if Pose[0][8][2] != 0 and Pose[0][9][2] != 0 and Pose[0][12][2] != 0:
                        if Pose[0][8][1] > Pose[1][8][1] and Pose[0][9][1] > Pose[1][9][1] and Pose[0][12][1] > \
                                Pose[1][12][1]:
                            n = 0  # 0先生是坐着的
                        else:
                            n = 1
                    else:
                        n = 1
                else:
                    n = 0
                helper = 'No'
            '''Helper'''  # n = user

            '''Compensation'''
            # neck_angle = round(Angle(5, 1, 8), 0)
            comps = np.arctan(abs((Pose[n][1][0] - Pose[n][8][0])) / (Pose[n][8][1] - Pose[n][1][1])) * 180 / np.pi
            comps = round(comps, 0)
            if comps < 10:
                string2 = 'Straight!'
                comps = 0
            else:
                if Pose[n][1][0] > Pose[n][8][0]:
                    string2 = 'Left Comps! ' + str(comps)
                else:
                    string2 = 'Right Comps! ' + str(abs(comps))

            if SSF_Max > Angle(1, 2, 3) and j == 1 and j1 == 1 and j2 == 1 and j3 == 1:
                SSF_Max = round(Angle(1, 2, 3), 0)  # 抬手时找角度最小
                # real_angle > Angle(1, 2, 3) - (180 - hip_angle - neck_angle)
            '''Compensation'''

            '''SSF'''
            if Pose[n][4][2] != 0 and Pose[n][2][2] != 0 and Pose[n][1][2] != 0 and Pose[n][3][2] != 0:
                '''Num'''
                SSF_Deviation = abs(SSF_Angle - Angle(1, 2, 3))
                SSF_Angle = Angle(1, 2, 3)
                if Pose[n][4][1] < Pose[n][2][1]:  # hands up
                    j3 = 1
                else:  # hands down
                    j3 = 0
                if j == 0 and j1 == 0 and j2 == 1 and j3 == 1:  # 0011抬手
                    SSF = SSF + 1
                j = j1
                j1 = j2
                j2 = j3
                '''Num'''

                '''Hold time'''
                if j == 1 and j1 == 1 and j2 == 1 and j3 == 1:  # 1111 hands up
                    SSF_Time = SSF_Time + 1  # 单位0.18s
                    if SSF_Time % SSF_Num == 0:  # 开始判定
                        if SSF_Sum / SSF_Num < 6:  # if hold？
                            if SSF_Flag == 0:
                                SSF_start = time()
                                SSF_Flag = 1
                        else:
                            SSF_Flag = 0
                        SSF_Sum = 0
                    else:  # 角度均值
                        SSF_Sum = SSF_Deviation + SSF_Sum
                else:
                    SSF_Flag = 0
                if SSF_Flag == 1 and round(time() - SSF_start, 2) > 1:  # 找到最后的hold值
                    SSF_Hold = round(time() - SSF_start, 2)
                '''Hold time'''

                '''Fill in database'''
                if j == 1 and j1 == 1 and j2 == 0 and j3 == 0:  # 1100放手
                    sql = "INSERT INTO " + week + "(SSF_Times, SSF_Angle, SSF_Hold, SSF_Comps ,SSF_DIY) VALUES (%s, %s, " \
                                                  "%s, %s, %s); "
                    cursor.execute(sql, (SSF_Row, 270 - SSF_Max, SSF_Hold, comps, helper))
                    db.commit()
                    SSF_Row = SSF_Row + 1
                    SSF_Max = 270
                    SSF_Hold = 0
                '''Fill in database'''

            else:
                BGR = cv2.putText(BGR, 'Move left', (5, H - 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)
            '''SSF'''
            ###################################################################################################
            '''Sitting Leg Lift'''
            if Pose[n][9][2] != 0 and Pose[n][10][2] != 0 and Pose[n][11][2] != 0:

                '''COMPS'''
                SLL_comps = np.arctan(
                    abs((Pose[n][9][1] - Pose[n][10][1]) / (Pose[n][10][0] - Pose[n][9][0]))) * 180 / np.pi
                SLL_comps = round(SLL_comps, 0)
                if SLL_comps < 15:
                    SLL_string2 = 'Horizontal'
                    SLL_comps = 0
                else:
                    SLL_string2 = 'Comps! ' + str(abs(SLL_comps))
                '''COMPS'''
                '''Num'''
                SLL_Deviation = SLL_Angle - Angle(9, 10, 11)
                SLL_Angle = Angle(9, 10, 11)
                if SLL_Max < SLL_Angle:
                    SLL_Max = round(SLL_Angle, 0)
                if SLL_Angle > 120:  # leg up
                    i3 = 1
                else:  # leg down
                    i3 = 0
                if i == 0 and i1 == 0 and i2 == 1 and i3 == 1:  # 0011抬脚
                    SLL = SLL + 1
                i = i1
                i1 = i2
                i2 = i3
                '''Num'''

                '''Hold time'''
                if i == 1 and i1 == 1 and i2 == 1 and i3 == 1:  # 1111 hands up
                    SLL_Time = SLL_Time + 1  # 单位0.18s
                    if SLL_Time % SLL_Num == 0:  # 开始判定
                        if SLL_Sum / SSF_Num < 6:  # if hold？
                            if SLL_Flag == 0:
                                SLL_start = time()
                                SLL_Flag = 1
                        else:
                            SLL_Flag = 0
                        SLL_Sum = 0
                    else:  # 角度偏差均值
                        SLL_Sum = SLL_Deviation + SLL_Sum
                else:
                    SLL_Flag = 0
                if SLL_Flag == 1 and round(time() - SLL_start, 2) > 1:  # 找到最后的hold值
                    SLL_Hold = round(time() - SLL_start, 2)
                '''Hold time'''

                '''Fill in database'''
                if i == 1 and i1 == 1 and i2 == 0 and i3 == 0:  # 1100放腿
                    sql = "INSERT INTO " + week + "(SLL_Times, SLL_Angle, SLL_Hold, SLL_Comps ,SLL_DIY) VALUES (%s, %s, " \
                                                  "%s, %s, %s); "
                    cursor = db.cursor()
                    cursor.execute(sql, (SLL_Row, SLL_Max, SLL_Hold, SLL_comps, helper))
                    db.commit()
                    SLL_Row = SLL_Row + 1
                    SLL_Max = 90
                    SLL_Hold = 0
                '''Fill in database'''

            else:
                BGR = cv2.putText(BGR, 'Move left', (5, H - 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)

            '''SLL'''
        else:
            BGR = cv2.putText(BGR, 'Move into camera', (5, H - 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)

        '''mirror_feedback'''
        string0 = 'SSF: ' + str(SSF) + ' Hold:' + str(SSF_Hold) + 's'
        BGR = cv2.putText(BGR, string0, (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)
        BGR = cv2.putText(BGR, 'Angle: ' + str(270 - SSF_Max), (5, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)
        BGR = cv2.putText(BGR, string2, (5, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)
        BGR = cv2.putText(BGR, helper, (5, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 2)
        ############################################################################################
        SLL_string0 = 'SLL: ' + str(SLL) + ' Hold:' + str(SLL_Hold) + 's'
        BGR = cv2.putText(BGR, SLL_string0, (W - 350, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        BGR = cv2.putText(BGR, 'Angle: ' + str(SLL_Max), (W - 350, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        BGR = cv2.putText(BGR, SLL_string2, (W - 350, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        BGR = cv2.putText(BGR, helper, (W - 350, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)

        '''控件显示'''
        # mirror feedback
        RGB = Image.fromarray(BGR)
        RGB = ImageTk.PhotoImage(RGB)
        canvas.create_image(0, 0, anchor='nw', image=RGB)  # 刷新图片，nw表示从西北角开始排列图片
        canvas.bg = RGB
        text2.set('Camera Open!')
        # times
        print(SSF, V)
        if int(SSF) < int(V):
            text3.set(str(SSF) + ' / ' + str(V))
        else:
            text3.set('Finish!')
        # progress bar
        if j == 1 and j1 == 1 and j2 == 1 and j3 == 1:  # hands up
            k = 0.4 * sx / 90  # 总长度0.4*sx
            n = k * (180 - SSF_Max)
        else:
            n = 0
        canvas3.coords(fill_line, (0, 0, n, 60))
        window.update()
        cv2.waitKey(1)


def video_stop():
    global video_flag, cap, canvas
    video_flag = False
    canvas.bg = '#c4c2c2'
    text2.set('Camera Close.')
    text3.set('0 / ' + str(V))
    cap.release()
    cv2.destroyAllWindows()


def SSF_video():
    global frame, canvas2, lock, SSF_Wait, sy
    SSF_Wait = 20
    lock.acquire()
    SSF_CAP = cv2.VideoCapture(video_ssf)
    while SSF_CAP.isOpened():
        ret, frame = SSF_CAP.read()  # 读取视频的一帧
        if frame is None:
            break
        frame = cv2.resize(frame, (round(0.62 * sy), round(0.46 * sy)))  # 前宽后高
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        image_file = ImageTk.PhotoImage(img)
        canvas2.create_image(0, 0, anchor='nw', image=image_file)  # 刷新图片，nw表示从西北角开始排列图片
        canvas2.bg = image_file
        cv2.waitKey(SSF_Wait)  # 控制播放速度
    lock.release()


def SLL_video():
    global frame, canvas2, lock, SLL_Wait
    SLL_Wait = 10
    lock.acquire()
    SLL_CAP = cv2.VideoCapture(video_sll)
    while SLL_CAP.isOpened():
        ret, frame = SLL_CAP.read()  # 从摄像头读取照片
        if frame is None:
            break
        frame = cv2.resize(frame, (round(0.62 * sy), round(0.46 * sy)))
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        image_file = ImageTk.PhotoImage(img)
        canvas2.create_image(0, 0, anchor='nw', image=image_file)  # 刷新图片，nw表示从西北角开始排列图片
        canvas2.bg = image_file
        cv2.waitKey(SLL_Wait)
    lock.release()


def thread1():
    t1 = Thread(target=SSF_video)
    t1.start()


def thread2():
    t2 = Thread(target=SLL_video)
    t2.start()


def thread3():
    t3 = Thread(target=video_start)
    t3.start()


def thread4():
    t4 = Thread(target=video_stop)
    t4.start()


def times(v):
    global V
    V = v
    text3.set('0 / ' + str(v))


#
# def thread5():
#
# def thread6():


'''创建GUI窗口'''
p = getcwd()
model = path.join(p, "models")
video_sll = path.join(p, "SLL.mp4")
video_ssf = path.join(p, "SSF.mp4")
print(model, video_ssf, video_sll)
lock = Lock()  # 创建lock函数
window = tk.Tk()  # window == top
window.title('Home Rehabilitation App')
sx = window.winfo_screenwidth()  # 获取屏幕宽
sy = window.winfo_screenheight()  # 获取屏幕高
window.geometry("%dx%d" % (sx, sy))  # 窗口至指定位置

'''画布'''
canvas = tk.Canvas(window, bg='#c4c2c2', height=0.68 * sy, width=0.906 * sy)  # 绘制camera画布
canvas.place(relx=0.48, rely=0.1, relheight=0.68, relwidth=0.906 * sy / sx)

canvas2 = tk.Canvas(window, bg='#c4c2c2', height=0.46 * sy, width=0.62 * sy)  # 绘制video画布
canvas2.place(relx=200 / sx, rely=108 / sy, relheight=500 / sy, relwidth=0.62 * sy / sx)

'''按钮'''
bt_start = tk.Button(window, text='Exercise!', command=thread3)
bt_start.place(relx=1220 / sx, rely=850 / sy, relheight=0.045, relwidth=0.06)

bt_stop = tk.Button(window, text='Stop!', command=thread4)
bt_stop.place(relx=1420 / sx, rely=850 / sy, relheight=0.045, relwidth=0.06)

# bt_db = tk.Button(window, text='Connect!', command=connect_db)
# bt_db.place(relx=330/sx, rely=750/sy, relheight=0.045, relwidth=0.06)
#
# bt_db = tk.Button(window, text='Disconnect', command=disconnect_db)
# bt_db.place(relx=530/sx, rely=750/sy, relheight=0.045, relwidth=0.06)

'''文本框'''
# text = tk.StringVar()
# text.set('Unconnected.')
# w = tk.Label(window, textvariable=text)
# w.place(relx=330/sx, rely=800/sy, relheight=0.045, relwidth=0.06)

text2 = tk.StringVar()
text2.set('Camera Close.')
w2 = tk.Label(window, textvariable=text2)
w2.place(relx=1220 / sx, rely=900 / sy, relheight=0.045, relwidth=0.06)

'''菜单'''
bar = tk.Menu(window)  # 创建顶级菜单
menu1 = tk.Menu(bar, tearoff=False)  # 创建菜单条
menu1.add_command(label="Sitting Shoulder Flexion", command=thread1)  # 创建下拉选项
menu1.add_command(label="Sitting Leg lift", command=thread2)
bar.add_cascade(label="Select Exercises", menu=menu1)

menu2 = tk.Menu(bar, tearoff=False)  # 创建菜单条
menu2.add_command(label="Connect", command=connect_db)  # 创建下拉选项
menu2.add_command(label="Disconnect", command=disconnect_db)
bar.add_cascade(label="Database", menu=menu2)

'''标题'''
title1 = tk.Label(window, text="Standard Video", font=('微软雅黑', 20), fg='Purple')
title2 = tk.Label(window, text="Mirror Feedback", font=('微软雅黑', 20), fg='Purple')
title3 = tk.Label(window, text="Params Setting", font=('微软雅黑', 20), fg='Purple')
title1.place(relx=300 / sx, rely=60 / sy, relheight=0.04, relwidth=0.2)
title2.place(relx=1200 / sx, rely=60 / sy, relheight=0.04, relwidth=0.2)
title3.place(relx=310 / sx, rely=650 / sy, relheight=0.04, relwidth=0.2)
window.config(menu=bar)

'''进度条'''
tk.Label(window, text='运动进度:', font=('微软雅黑', 15), ).place(relx=930 / sx, rely=960 / sy)
canvas3 = tk.Canvas(window, bg="white")
canvas3.place(relx=1030 / sx, rely=950 / sy, relheight=0.04, relwidth=0.4)
fill_line = canvas3.create_rectangle(0, 0, 0, 0, fill="green")

'''记次'''
text3 = tk.StringVar()
text3.set('0 / 0')
w3 = tk.Label(window, textvariable=text3, font=('微软雅黑', 20))
w3.place(relx=1800 / sx, rely=940 / sy, relheight=0.06, relwidth=0.06)

'''参数'''
s = tk.Scale(window, label='Repetitions', from_=0, to=10, orient=tk.HORIZONTAL,
             length=200, showvalue=1, tickinterval=5, resolution=1, command=times)
s.place(relx=260 / sx, rely=700 / sy)


window.mainloop()
