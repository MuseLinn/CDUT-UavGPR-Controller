# coding:UTF-8
"""
    HWT905-TTL姿态传感器
"""
import time
import datetime
from sys import platform

import lib.device_model as device
from src.lib.data_processor.roles.jy901s_dataProcessor import JY901SDataProcessor
from src.lib.protocol_resolver.roles.wit_protocol_resolver import WitProtocolResolver

"注意更改串口号（portNAME）"
"HWT905上位机，可显示时间、温度、加速度、角速度、角度、磁场"
# 初始化设备初始化设备初始化设备初始化设备初始化设备初始化设备初始化设备初始化设备初始化设备初始化设备

welcome = """
欢迎使用维特智能示例程序    Welcome to the Wit-Motoin sample program
"""
_writeF = None                    #写文件  Write file
_IsWriteF = False                 #写文件标识    Write file identification

def readConfig(device):
    # 读取某个寄存器的配置信息可调用设备模型的readConfig(regAddr, regCount)
    # 这个函数，
    # 这个函数第一个参数regAddr：起始寄存器地址；第二个参数regCount：寄存器的个数（注意这里必须是连续的寄存器地址）
    """
    读取配置信息示例    Example of reading configuration information
    :param device: 设备模型 Device model
    :return:
    """
    tVals = device.readReg(0x02,3)  #读取数据内容、回传速率、通讯速率   Read data content, return rate, communication rate
    if (len(tVals)>0):
        print("返回结果：" + str(tVals))
    else:
        print("无返回")
    tVals = device.readReg(0x23,2)  #读取安装方向、算法  Read the installation direction and algorithm
    if (len(tVals)>0):
        print("返回结果：" + str(tVals))
    else:
        print("无返回")

def setConfig(device):
    """
    设置配置信息示例    Example setting configuration information
    :param device: 设备模型 Device model
    :return:
    """
    device.unlock()                # 解锁 unlock
    time.sleep(0.1)                # 休眠100毫秒    Sleep 100ms
    device.writeReg(0x03, 6)       # 设置回传速率为10HZ    Set the transmission back rate to 10HZ
    time.sleep(0.1)                # 休眠100毫秒    Sleep 100ms
    device.writeReg(0x23, 0)       # 设置安装方向:水平、垂直   Set the installation direction: horizontal and vertical
    time.sleep(0.1)                # 休眠100毫秒    Sleep 100ms
    device.writeReg(0x24, 0)       # 设置安装方向:九轴、六轴   Set the installation direction: nine axis, six axis
    time.sleep(0.1)                # 休眠100毫秒    Sleep 100ms
    device.save()                  # 保存 Save
#写入多个寄存器时，必须间隔一定的时间
def AccelerationCalibration(device):
    """
    加计校准    Acceleration calibration
    :param device: 设备模型 Device model
    :return:
    """
    device.AccelerationCalibration()                 # Acceleration calibration
    print("加计校准结束")

def FiledCalibration(device):
    """
    磁场校准    Magnetic field calibration
    :param device: 设备模型 Device model
    :return:
    """
    device.BeginFiledCalibration()                   # 开始磁场校准   Starting field calibration
    if input("请分别绕XYZ轴慢速转动一圈，三轴转圈完成后，结束校准（Y/N)？").lower()=="y":
        device.EndFiledCalibration()                 # 结束磁场校准   End field calibration
        print("结束磁场校准")

def onUpdate(DeviceModel):
    """
    数据更新事件  Data update event
    :param DeviceModel: 设备模型    Device model
    :return:
    """
    # t1=datetime.datetime.now().microsecond
    # t3=time.mktime(datetime.datetime.now().timetuple())
    # t2=datetime.datetime.now().microsecond
    # t4=time.mktime(datetime.datetime.now().timetuple())
    # strTime=str(t3)+"."+str(t1)+"-"+str(t4)+"."+str(t2)
    # print(strTime)
    current_time=datetime.datetime.now()

    print("芯片时间:", current_time
         , " 温度:" + str(DeviceModel.getDeviceData("temperature"))
         , " 加速度：" + str(DeviceModel.getDeviceData("accX")) +"/"+  str(DeviceModel.getDeviceData("accY")) +"/"+ str(DeviceModel.getDeviceData("accZ"))
         ,  " 角速度:" + str(DeviceModel.getDeviceData("gyroX")) +"/"+ str(DeviceModel.getDeviceData("gyroY")) +"/"+ str(DeviceModel.getDeviceData("gyroZ"))
         , " 角度:" + str(DeviceModel.getDeviceData("angleX")) +"/"+ str(DeviceModel.getDeviceData("angleY")) +"/"+ str(DeviceModel.getDeviceData("angleZ"))
        , " 磁场:" + str(DeviceModel.getDeviceData("magX")) +"/"+ str(DeviceModel.getDeviceData("magY"))+"/"+ str(DeviceModel.getDeviceData("magZ"))
        , " 经度:" + str(DeviceModel.getDeviceData("lon")) + " 纬度:" + str(DeviceModel.getDeviceData("lat"))
        , " 航向角:" + str(DeviceModel.getDeviceData("Yaw")) + " 地速:" + str(DeviceModel.getDeviceData("Speed"))
         , " 四元素:" + str(DeviceModel.getDeviceData("q1")) + "," + str(DeviceModel.getDeviceData("q2")) + "," + str(DeviceModel.getDeviceData("q3"))+ "," + str(DeviceModel.getDeviceData("q4"))
          )
    if (_IsWriteF):    #记录数据    Record data
        Tempstr = " " + str(DeviceModel.getDeviceData("current_time"))
        Tempstr += "\t"+str(DeviceModel.getDeviceData("accX")) + "\t"+str(DeviceModel.getDeviceData("accY"))+"\t"+ str(DeviceModel.getDeviceData("accZ"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("gyroX")) +"\t"+ str(DeviceModel.getDeviceData("gyroY")) +"\t"+ str(DeviceModel.getDeviceData("gyroZ"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("angleX")) +"\t" + str(DeviceModel.getDeviceData("angleY")) +"\t"+ str(DeviceModel.getDeviceData("angleZ"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("temperature"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("magX")) +"\t" + str(DeviceModel.getDeviceData("magY")) +"\t"+ str(DeviceModel.getDeviceData("magZ"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("lon")) + "\t" + str(DeviceModel.getDeviceData("lat"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("Yaw")) + "\t" + str(DeviceModel.getDeviceData("Speed"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("q1")) + "\t" + str(DeviceModel.getDeviceData("q2"))
        Tempstr += "\t" + str(DeviceModel.getDeviceData("q3")) + "\t" + str(DeviceModel.getDeviceData("q4"))
        Tempstr += "\r\n"
        _writeF.write(Tempstr)

def startRecord():
    """
    开始记录数据  Start recording data
    :return:
    """
    global _writeF
    global _IsWriteF
    _writeF = open(str(datetime.datetime.now().strftime('%Y%m%d%H%M%S')) + ".txt", "w")    #新建一个文件
    _IsWriteF = True                                                                        #标记写入标识
    Tempstr = "Chiptime"
    Tempstr +=  "\tax(g)\tay(g)\taz(g)"
    Tempstr += "\twx(deg/s)\twy(deg/s)\twz(deg/s)"
    Tempstr += "\tAngleX(deg)\tAngleY(deg)\tAngleZ(deg)"
    Tempstr += "\tT(°)"
    Tempstr += "\tmagx\tmagy\tmagz"
    Tempstr += "\tlon\tlat"
    Tempstr += "\tYaw\tSpeed"
    Tempstr += "\tq1\tq2\tq3\tq4"
    Tempstr += "\r\n"
    _writeF.write(Tempstr)
    print("开始记录数据")

def endRecord():
    """
    结束记录数据  End record data
    :return:
    """
    global _writeF
    global _IsWriteF
    _IsWriteF = False             # 标记不可写入标识    Tag cannot write the identity
    _writeF.close()               #关闭文件 Close file
    print("结束记录数据")

if __name__ == '__main__':

    print(welcome)
    """
    初始化一个设备模型   Initialize a device model
    """
    device = device.DeviceModel(
        "HWT905-TTL",
        WitProtocolResolver(),
        JY901SDataProcessor(),
        "51_0"
    )


    if platform.lower() == 'linux':
        device.serialConfig.portName = "/dev/ttyUSB0"   #设置串口   Set serial port
    else:
        device.serialConfig.portName = "COM3"          #设置串口   Set serial port
    device.serialConfig.baud = 9600                     #设置波特率  Set baud rate
    device.openDevice()                                 #打开串口   Open serial port
    readConfig(device)                                  #读取配置信息 Read configuration information
    device.dataProcessor.onVarChanged.append(onUpdate)  #数据更新事件 Data update event

    startRecord()                                       # 开始记录数据    Start recording data
    input()
    device.closeDevice()
    endRecord()                                         #结束记录数据 End record data
