###################################################################################################################################################
#  Atlas-I2C-Driver-JQ.py - A python based code to connect to, read data from, and send commands to Atlas Scientific Devices over a I2C Protocol
#
#  Author: John Quinn
#
#  Created: 9/16/24
#
#  Purpose: Mid level command singnaling to the atlas devices and library of commands for use in higher level functionality in Novus Project
#
#  Refrences:
#       ADD DOCUMENTAION HERE 
#       
###################################################################################################################################################
# SEction TITLE
import serial
import sys
import time
import csv
from time import sleep
from pathlib import Path
from serial import SerialException

import io
import fcntl
import copy
import string

###################################################################################################################################################
# Class Definition - Atlas_I2C
#       Atlas_I2C

def read_recieve_all(device_list):
    '''
    write a command to the ALL I2C boards in passed in "Device_list" (device list should be a list of insances of this class!), wait the correct timeout, 
    and read the response
    '''
    responses = []
    
    for dev in device_list:
        dev.write("R")
        
    current_timeout = device_list[0].get_command_timeout("R")
    
    if not current_timeout:
        return "sleep mode"
    
    else:
        time.sleep(current_timeout)
        # print(current_timeout)
        for dev in device_list:
            responses.append(dev.read().strip('\x00').replace("\x00",''))
        return responses
            

class Config_AtlasI2C:
    def __init__():
        pass

    def print_device_info(device_list, device):
        for i in device_list:
            if(i == device):
                print("--> " + i.get_device_info())
            else:
                print(" - " + i.get_device_info())
        #print("")
    
    def get_devices():
        device = Atlas_I2C()
        device_address_list = device.list_i2c_devices()
        device_list = []
        
        for i in device_address_list:
            device.set_i2c_address(i)
            response = device.query("I")
            try:
                moduletype = response.split(",")[1] 
                response = device.query("name,?").split(",")[1]
            except IndexError:
                print(">> WARNING: device at I2C address " + str(i) + " has not been identified as an EZO device, and will not be queried") 
                continue
            device_list.append(Atlas_I2C(address = i, moduletype = moduletype, name = response))
        return device_list 

class Atlas_I2C:

    # the timeout needed to query readings and calibrations
    LONG_TIMEOUT = .9 # Changed from 1.5 as atlas default
    # timeout for regular commands
    SHORT_TIMEOUT = .3
    # the default bus for I2C on the newer Raspberry Pis, 
    # certain older boards use bus 0
    DEFAULT_BUS = 1
    # the default address for the sensor
    DEFAULT_ADDRESS = 98
    LONG_TIMEOUT_COMMANDS = ("R", "CAL")
    SLEEP_COMMANDS = ("SLEEP", )

    def __init__(self, address=None, moduletype = "", name = "", bus=None):
            '''
            open two file streams, one for reading and one for writing
            the specific I2C channel is selected with bus
            it is usually 1, except for older revisions where its 0
            wb and rb indicate binary read and write
            '''
            self._address = address or self.DEFAULT_ADDRESS
            self.bus = bus or self.DEFAULT_BUS
            self._long_timeout = self.LONG_TIMEOUT
            self._short_timeout = self.SHORT_TIMEOUT
            self.file_read = io.open(file="/dev/i2c-{}".format(self.bus), 
                                    mode="rb", 
                                    buffering=0)
            self.file_write = io.open(file="/dev/i2c-{}".format(self.bus),
                                    mode="wb", 
                                    buffering=0)
            self.set_i2c_address(self._address)
            self._name = name
            self._module = moduletype

	
    @property
    def long_timeout(self):
        return self._long_timeout

    @property
    def short_timeout(self):
        return self._short_timeout

    @property
    def name(self):
        return self._name
        
    @property
    def address(self):
        return self._address
        
    @property
    def moduletype(self):
        return self._module
        
    def set_i2c_address(self, addr):
        '''
        set the I2C communications to the slave specified by the address
        the commands for I2C dev using the ioctl functions are specified in
        the i2c-dev.h file from i2c-tools
        '''
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
        self._address = addr

    def write(self, cmd):
        '''
        appends the null character and sends the string over I2C
        '''
        cmd += "\00"
        self.file_write.write(cmd.encode('latin-1'))

    def handle_raspi_glitch(self, response):
        '''
        Change MSB to 0 for all received characters except the first 
        and get a list of characters
        NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, 
        and you shouldn't have to do this!
        '''
        if self.app_using_python_two():
            return list(map(lambda x: chr(ord(x) & ~0x80), list(response)))
        else:
            return list(map(lambda x: chr(x & ~0x80), list(response)))
            
    def app_using_python_two(self):
        return sys.version_info[0] < 3

    def get_response(self, raw_data):
        if self.app_using_python_two():
            response = [i for i in raw_data if i != '\x00']
        else:
            response = raw_data

        return response

    def response_valid(self, response):
        valid = True
        error_code = None
        if(len(response) > 0):
            
            if self.app_using_python_two():
                error_code = str(ord(response[0]))
            else:
                error_code = str(response[0])
                
            if error_code != '1': #1:
                valid = False

        return valid, error_code

    def get_device_info(self):
        if(self._name == ""):
            return self._module + " " + str(self.address)
        else:
            return self._module + " " + str(self.address) + " " + self._name
        
    def read(self, num_of_bytes=31):
        '''
        reads a specified number of bytes from I2C, then parses and displays the result
        '''
        
        raw_data = self.file_read.read(num_of_bytes)
        response = self.get_response(raw_data=raw_data)
        #print(response)
        is_valid, error_code = self.response_valid(response=response)

        if is_valid:
            char_list = self.handle_raspi_glitch(response[1:])
            result = "Success " + self.get_device_info() + ": " +  str(''.join(char_list))
            #result = "Success: " +  str(''.join(char_list))
        else:
            result = "Error " + self.get_device_info() + ": " + error_code

        return result

    def get_command_timeout(self, command):
        timeout = None
        if command.upper().startswith(self.LONG_TIMEOUT_COMMANDS):
            timeout = self._long_timeout
        elif not command.upper().startswith(self.SLEEP_COMMANDS):
            timeout = self.short_timeout

        return timeout

    def query(self, command):
        '''
        write a command to the board, wait the correct timeout, 
        and read the response
        '''
        self.write(command)
        current_timeout = self.get_command_timeout(command=command)
        if not current_timeout:
            return "sleep mode"
        else:
            time.sleep(current_timeout)
            return self.read()
        
    
    def close(self):
        self.file_read.close()
        self.file_write.close()

    def list_i2c_devices(self):
        '''
        save the current address so we can restore it after
        '''
        prev_addr = copy.deepcopy(self._address)
        i2c_devices = []
        for i in range(0, 128):
            try:
                self.set_i2c_address(i)
                self.read(1)
                i2c_devices.append(i)
            except IOError:
                pass
        # restore the address we were using
        self.set_i2c_address(prev_addr)

        return i2c_devices


# ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
#     def __init__(self):
#         pass
    
    
#     def atlas_configurator(device_names = [] ,port_addresses = []):
#         baud_rates = [9600 for _ in range(4)]
#         timeouts = [1 for _ in range(4)]
#         config_row = zip(device_names, port_addresses, baud_rates, timeouts)
#         top_row = ['Atlas Device Name', 'UART Port Address', 'UART Baud Rate', 'Baud Timeout']

#         p = Path(__file__).with_name('Atlas_Devices_config.csv')

#         with p.open('w') as file:
#             # Create a CSV writer object
#             writer = csv.writer(file)

#             # Write the data rows to the CSV file
#             writer.writerow(top_row)
#             writer.writerows(config_row)
#             print("CSV file created successfully.")
#             pass


#     def init_Atlas(self,device_name, printout = False):
#         p = Path(__file__).with_name('Atlas_Devices_config.csv')
#         with p.open('r') as file:
#             reader=csv.reader(file)
#             for row in reader:
#                 if row[0] == device_name:
#                     self.device_name = device_name
#                     self.UART_port = row[1]
#                     self.baudrate = int(row[2])
#                     self.timeout = int(row[3])
#                     if printout == True:
#                         print('\nInitalization Sucsessful with following Info \nDeivce Name:',device_name,'\n'
#                                 'Device UART Address:',self.UART_port,'\n')
#                     if printout == False:
#                         print('\nInitalization Sucsessful \n Device',device_name,'found, config data loaded\n    *Set printout kwarg to True for more info')
        

#     def open_UART(self):
#         try:
#             self.device_serial_instance = serial.Serial(self.UART_port,self.baudrate,timeout=self.timeout)
#             self.device_serial_instance.reset_input_buffer()
#             self.device_serial_instance.reset_output_buffer()
#             print('\nUART Port Opened for',self.device_name)
            
#         except serial.SerialException as e:
#             print( "Error port could not be opened, ", e)
#             sys.exit(0)    


#     def close_UART(self):
#         try:
#             self.device_serial_instance.close()
#             print('\nUART Port Closed for',self.device_name)

#         except serial.SerialException as e:
#             print( "Error  UART Port could not be closed", e)


#     def read_line(self):
#         """
#         taken from the ftdi library and modified to 
#         use the ezo line separator "\r"
#         """
#         line_break = len(b'\r')
#         line_buffer = []
#         while True:
#             next_char = self.device_serial_instance.read()
#             if next_char == b'':
#                 break
#             line_buffer.append(next_char)
#             if (len(line_buffer) >= line_break and
#                     line_buffer[-line_break:] == [b'\r']):
#                 break
#         return b''.join(line_buffer)
        

#     def read_lines(self):
#         """
#         also taken from ftdi lib to work with modified readline function
#         """
#         lines = []
#         try:
#             line = self.read_line()
#             lines.append(line)
#             return lines
#         except SerialException as e:
#             print( "Error, ", e)
#             return None	
    
#     def parse_lines(self):
#         lines = self.read_lines()
#         for i in range(len(lines)):
#             return lines[i].decode('utf-8')
    
#     def response(self):
#         """
#         also taken from ftdi lib to work with modified readline function
#         """
#         try:
#             self.resp_line_bytes = self.device_serial_instance.read_until(b'/n')
#             self.resp_line_str_list = self.resp_line_bytes.decode('utf-8')
#             self.resp_line_str_list = self.resp_line_str_list.split('\r')
    
#         except SerialException as e:
#             print( "Error, ", e)
#             return None	

#     def send_cmd(self,cmd):
#         """
#         Send command to the Atlas Sensor.
#         Before sending, add Carriage Return at the end of the command.
#         :param cmd:
#         :return:
#         """
#         buf = cmd + "\r"     	# add carriage return
#         try:
#             self.device_serial_instance.write(buf.encode('utf-8'))
#             return True
#         except SerialException as e:
#             print ("Error, ", e)
#             return None

#     def read_single(self):
#         self.send_cmd('R')

# class Atlas_Peri(Atlas_Lib):
#     def __init__(self):
#         pass

  
#     def cal(self,actual_vol):
#         self.send_cmd('Cal,'+actual_vol)

#     def clear_cal(self):
#         self.send_cmd('Cal,clear')

#     def cal_check(self):
#         self.send_cmd('Cal,?')

#     def disp_vol(self,vol2disp):
#         '''Dispenses a specified volume through the pump'''
#         cmd2send = 'D,'+ str(vol2disp)
#         self.send_cmd(cmd2send)

#     def invert(self):
#         """Reverses the flow direction of the pump"""
#         self.send_cmd('Invert')

#     def cont_read(self,setting = True):
#         '''Changes continous reading setting for device 

#             This is on and running at 1 Reading/Second by default 
        
#             For setting varbiable 
#             True = Enable Continous Readings
#             False = Disable Readings
             
#             read_freq is the frequency (in seconds) that measuments will be made '''
#         if setting == True:
#             cmd_str = 'C,*'
#         elif setting == False:
#             cmd_str = 'C,0'

#         self.send_cmd(cmd_str) 


# class Altas_pH(Atlas_Lib):
#     def __init__(self):
#         pass

#     def cal(self,measured_val, cal_pt = str):
#         '''Function ot calibrate the pH meter
#         cal_pt vairable should always be a string of one of the following 
#             low - for lowest pH calibration'''
#         cmd2send = 'Cal,'+cal_pt+str(measured_val)
#         self.send_cmd(cmd2send)

#     def clear_cal(self):
#         self.send_cmd('Cal,clear')

#     def cal_check(self):
#         self.send_cmd('Cal,?')

#     def cont_read(self,setting = True, read_freq = 1):
#         '''Changes continous reading setting for device 

#             This is on and running at 1 Reading/Second by default 
        
#             For setting varbiable 
#             True = Enable Continous Readings
#             False = Disable Readings
             
#             read_freq is the frequency (in seconds) that measuments will be made '''
#         if setting == True:
#             cmd_str = 'C,'+str(read_freq)
#         elif setting == False:
#             cmd_str = 'C,0'

#         self.send_cmd(cmd_str) 
    
#     def read_avg(self,sample_time=5):
#         self.response()
#         input_list = self.resp_line_str_list
#         str_pH_reads = [item for item in input_list[-(sample_time+1):-1] if not any(c.isalpha() for c in item)]
#         pH_reads = []
#         for item in str_pH_reads:
#             pH_reads.append(float(item))
#         print(pH_reads)
#         self.pH_Avg = sum(pH_reads)/len(pH_reads)
#         self.pH_Avg_rounded_1d = round(self.pH_Avg,1)
#         self.pH_Avg_rounded_2d = round(self.pH_Avg,2)
#         return self.pH_Avg_rounded_1d

#     def stream_pH(self,stream_duration,read_freq=1,dec_pts=1):
#         start_time = time.time()
#         end_time = start_time + stream_duration
#         while time.time() < end_time:
#             try:
#                 self.send_cmd("R")
#                 lines = self.read_lines()
#                 for i in range(len(lines)):
#                     # print lines[i]
#                     if lines[i][0] != b'*'[0]:
#                         self.inst_value = lines[i].decode('utf-8')
#                         self.inst_value_rd1 = str(round(float(self.inst_value),1))
#                         self.inst_value_rd2 = str(round(float(self.inst_value),2))
#                         if dec_pts == 1:
#                             print( "Response: " + self.inst_value_rd1)
#                         if dec_pts == 2:
#                             print( "Response: " + self.inst_value_rd2)
#                         if dec_pts == 3:
#                             print( "Response: " + self.inst_value)
#                 time.sleep(read_freq)

#             except KeyboardInterrupt: 		# catches the ctrl-c command, which breaks the loop above
#                 print("Continuous polling stopped")
	
