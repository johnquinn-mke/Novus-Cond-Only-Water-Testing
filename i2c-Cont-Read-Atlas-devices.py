####################################   Package Imports    ####################################

from Atlas_I2C_Driver_JQ import Atlas_I2C, Config_AtlasI2C, read_recieve_all
from time import sleep, time
import datetime
import csv
# import sm_tc
# from tricont_cseries_DT_Driver import cseries_DT


####################################   Define Stability Function    ####################################
def check_stability(reading, reading_list, sigma, stability_dict, probe_name):
    delta = round(abs(reading - reading_list[-2]),7)
    if delta > 4.5 * sigma:
        stability_dict[probe_name] += 1
        is_stable = 'Not Stable'
    else:
        stability_dict[probe_name] = 0
        is_stable = 'Stable' 
    return delta, is_stable

# class SensorError(Exception):
#     pass

####################################   Define Stability Function    ####################################

def main():
    # Constants for sigma values, replace with actual calibration values
    # SIGMA_COND = 0.01  # Sigma value for conductivity probe
    # SIGMA_PH = 0.008309563    # Sigma value for pH probe ; AVG From previous testing w/o

    filename_s = input("Enter Name for Datalog File: ")

    filename = f"{filename_s}.csv"
####################################   Configure Hardware     ####################################
    ## Initalize Atlas Deiveces Over I2C and assign device addresses to sensors
    
    device_list = Config_AtlasI2C.get_devices()

        
    # pH_Mettler = device_list[0]
    # pH_Unitrode = device_list[1]
    # pH_Ecotrode = device_list[2]
    
    # RTD_Ecotrode = device_list[3]
    # RTD_Ref  = device_list[4]
    # RTD_Unitrode = device_list[5]
    
    # Press_1 = device_list[6]
    # Press_2 = device_list[7]
    
    # Config_AtlasI2C.print_device_info(device_list, device_list[0])
    # print("Atlas Device List", device_list)

    ## Initalize Sequent Microsystems Thermocouple Reader
 
    # therm_Coupl = sm_tc.SMtc(0)  


    ##    TEST PROBE READING! ###

    # Atlas_I2C.write(pH_Mettler,'R')
    # Atlas_I2C.write(pH_Unitrode,'R')
    # Atlas_I2C.write(pH_Ecotrode,'R')

    
    # Atlas_I2C.write(RTD_Ecotrode,'R')
    # Atlas_I2C.write(RTD_Ref,'R')
    # Atlas_I2C.write(RTD_Unitrode,'R')
    
    # Atlas_I2C.write(Press_1,'R')
    # Atlas_I2C.write(Press_2,'R')
    
    # timeout = device_list[0].get_command_timeout('R')

    # sleep(timeout)
    # for dev in device_list:
    #     print('Probe Response'+ dev.read())
    
    
    # NTC_Mettler = therm_Coupl.get_temp(1)
    # message = f"Mettler Thermistor Response: {NTC_Mettler} Celcius"
    # print(message)
    
    
    
    # ####################################   Cont Read Protocol    ####################################     
    Unitrode_pH_list = []
    Ecotrode_pH_list = []
    Mettler_pH_list = []
    
    temp_1_list = []
    temp_2_list = []
    Ref_temp_list = []
    
    # Press_1_list = []
    # Press_2_list = []    
    
    # pH_stability_dict = {'Uni': 0, 'Eco': 0, 'Mettler':0}  # Tracks consecutive instability
    
    # stable_period = 0  # Tracks consecutive stable period
 
    with open(filename, "w", newline='') as DataoutCsv:
        csv_writer = csv.writer(DataoutCsv, delimiter=';')
        csv_writer.writerow(["Time (Y-M-D-H-M-S)","Time from Start (Seconds)", "Loop Time (Seconds)", "K1.0 Conductivity Reading (uS/cm)" , "K0.1 #1 Conductivity Reading (uS/cm)", "K0.1 #2 Conductivity Reading (uS/cm)", "K0.1 #3 Conductivity Reading (uS/cm)"])
        # csv_writer.writerow(["Time (Y-M-D-H-M-S)","Time from Start (Seconds)", "Loop Time (Seconds)", "Unitrode Reading (pH)", "Unitrode Temp (C)", "Ecotrode Reading (pH)", "Ecotrode Temp (C)","Mettler Reading (pH)", "Reference Themrocouple Temp (C)"])
    try:
        time_elapsed_start = time()
        loop_time = None
        
        while True:
            loop_time_start = time()
           
            now = datetime.datetime.now()
            time_elapsed_loop_end = time()
            time_elapsed_overall = time_elapsed_loop_end - time_elapsed_start
            I2C_readings = read_recieve_all(device_list)
            
            reading_pH_Mettler = I2C_readings[0].split(':')
            reading_pH_Unitrode = I2C_readings[1].split(':')
            reading_pH_Ecotrode = I2C_readings[2].split(':')
            
            reading_Temp_1= I2C_readings[3].split(':')
            # reading_Temp_2 = I2C_readings[3].split(':')        
            # reading_RTD_Ref  = I2C_readings[5].split(':')
            print(reading_Temp_1)

            if reading_pH_Mettler or reading_pH_Unitrode or reading_pH_Ecotrode or reading_Temp_1 is not float:
               pass

            if reading_pH_Mettler[-1] != b'*OK\r' :
                Ecotrode_pH_list.append(float(reading_pH_Ecotrode[1]))
                Unitrode_pH_list.append(float(reading_pH_Unitrode[1]))
                Mettler_pH_list.append(float(reading_pH_Mettler[1]))
                
                temp_1_list.append(float(reading_Temp_1[1]))
                # temp_2_list.append(float(reading_Temp_2[1]))
                # Ref_temp_list.append(float(reading_RTD_Ref[1]))
                
                # Press_1_list.append(float(reading_Press_1[1]))
                # Press_2_list.append(float(reading_Press_2[1]))

                if Ecotrode_pH_list[0] or Unitrode_pH_list[0] or Mettler_pH_list[0] or temp_1_list[0] is not float:
                    pass
                
                    print('\n')
                    print(f"Time Elapsed:{time_elapsed_overall}\nK1.0 Conductivity:{reading_pH_Mettler[1]} uS/cm \nK0.1 #1 Conductivity:{reading_pH_Unitrode[1]} uS/cm \nK0.1 #2 Conductivity:{reading_pH_Ecotrode[1]} uS/cm \nK0.1 #3 Conductivity:{reading_Temp_1[1]} uS/cm")


                    # print(f"Time Elapsed:{time_elapsed_overall}\nTemp 1:{reading_Temp_2[1]} C     Temp 2:{reading_Temp_1[1]} C     Ref Temp:{reading_RTD_Ref[1]} C")
                    # print(f"Ecotrode:{reading_pH_Ecotrode[1]} pH     Unitrode:{reading_pH_Unitrode[1]} pH     Mettler:{reading_pH_Mettler[1]} pH")

                # if len(Unitrode_pH_list) > 2 and len(Ecotrode_pH_list) and len(Mettler_pH_list) > 2:
                #         # Check for stability
                #         Ecotrode_delta, Ecotrode_stability = check_stability(float(reading_pH_Ecotrode[1]), Ecotrode_pH_list, SIGMA_PH, pH_stability_dict, 'Eco')
                #         Unitrode_delta, Unitrode_stability = check_stability(float(reading_pH_Unitrode[1]), Unitrode_pH_list, SIGMA_PH, pH_stability_dict, 'Uni')
                #         Mettler_delta, Mettler_stability = check_stability(float(reading_pH_Mettler[1]), Mettler_pH_list, SIGMA_PH, pH_stability_dict, 'Mettler')
                        
                #         print(f"Time Elapsed:{time_elapsed_overall}     Stable Count: {stable_period}\n\nUnitrode :{reading_pH_Unitrode[1]}pH       Stable?:{Unitrode_stability}    Delta:{Unitrode_delta} \nEcotrode :{reading_pH_Ecotrode[1]}pH       Stable?:{Ecotrode_stability}    Delta:{Ecotrode_delta} \nMettler :{reading_pH_Mettler[1]}pH       Stable?:{Mettler_stability}    Delta:{Mettler_delta}\n\n\n")

                #         if Ecotrode_stability == 'Stable' and Ecotrode_stability == 'Stable' and Mettler_stability == 'Stable':
                #             stable_period += 1
                #             if stable_period > 30:  # Reached 30 seconds of initial stability
                #                 pump_active = True
                #         else:
                #             stable_period = 0  # Reset stable period if not stable
                #             pump_active = False         
                                                

                    now = datetime.datetime.now()
                    loop_time_end = time()
                    loop_time = (loop_time_end-loop_time_start)
                    with open(filename, "a", newline='') as DataoutCsv:
                        csv_writer = csv.writer(DataoutCsv, delimiter=';')
                        csv_writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"),time_elapsed_overall, loop_time, reading_pH_Mettler[1],reading_pH_Unitrode[1],reading_pH_Ecotrode[1], reading_Temp_1[1]])
                    
                # if loop_time == None:
                #     loop_time_end = time()
                #     loop_time = (loop_time_end-loop_time_start)                
                # print("Loop Time: ",loop_time)
                # sleep(1-(loop_time)) 
                
    except KeyboardInterrupt:
            print("Data Logging Stopped By User")
            exit()  



if __name__ == "__main__":
    main()