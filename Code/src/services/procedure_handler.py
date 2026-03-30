import threading
import queue
import logging
import time
from datetime import datetime, timedelta
from services.move_registry import MoveRegistry
# pylint: disable=line-too-long


class ProcedureHandler(threading.Thread):
    """This class controls the main procedure thread, which calls functions .
    """

    def __init__(self, move_registry):
        super().__init__(name="ProcedureHandler",daemon=True)
        
        self.logger = logging.getLogger("Main Logger")
        self.move_registry = move_registry

        self.procedure = None
        self.current_step = 0
        
        self.paused = threading.Event()
        self.started = threading.Event()
 
        self.procedure_timer = Timer()
        self.start()

        self.error_flag = False
        self.error_step_index = None    

    def set_procedure(self, procedure: list):
        """Set the procedure to be run.
        Args:
            procedure (list): list of moves to run.
        """
        if self.started.is_set():
            self.logger.error("Cannot change moves until procedure stops")
            return
        
        if not self.move_registry.validate_moves(procedure):
            self.logger.error("Invalid moves in procedure")
            return
         
        self.procedure = procedure

    def run(self):
        """Run the procedure
        """
        while True:
            # wait until user has started procedure
            self.started.wait()
            
            self.current_step = 0
            
            while self.started.is_set() and (self.current_step < len(self.procedure)):
                
                if self.started.is_set() == False:
                    self.logger.info("Stopping")
                    break
                
                move = self.procedure[self.current_step]
                
                self.logger.debug(f"Executing move {self.current_step}")
                func_name = move[0]
                func_args = move[1:]

                # try running the move, stopping if there are any errors
                try:
                    self.move_registry.move_dict[func_name](*func_args)
                except Exception as e:
                    self.logger.error(f"Error while running procedure: {e}")
                    self.error_flag = True
                    self.error_step_index = self.current_step
                    break
                self.logger.debug(f"Move Done")
                self.current_step+=1
                time.sleep(0.2)
            
                # if procedure is paused after finishing previous move
                if self.paused.is_set():
                    self.logger.info("Paused")
                    self.procedure_timer.pause()
                    while self.paused.is_set():
                        time.sleep(0.1)
                    self.procedure_timer.unpause()
                    self.logger.info("Unpaused")
            
            self.stop()
            self.logger.debug("Procedure Ended")

    def begin(self):
        """Begin the procedure
        """
        if not self.procedure:
            self.logger.error("No procedure set")
            return
   
        self.started.set()
        self.paused.clear()
        self.procedure_timer.start()
        self.logger.info("Starting Procedure...")

    def stop(self):
        """Stop the procedure.
        """
        self.started.clear()
        self.paused.clear()
        self.procedure_timer.pause()
        self.logger.info("Stopping procedure...")
        
            
    def kill(self):
        self.move_registry.kill()
        self.logger.error("Machine shut down. Reboot required")

    def pause(self):
        """Pause the procedure."""
        self.paused.set()
        self.logger.info("Pausing procedure...")

    def resume(self) -> None:
        """Resume the procedure."""
        self.paused.clear()
        self.logger.info("Resuming procedure...")
        
    def get_time_elapsed(self) -> timedelta:
        return self.procedure_timer.get_time()
        
    def get_progress(self) -> float:
        if self.procedure is None:
            return 0
      
        return self.current_step / len(self.procedure)
    
    #set the number of procedurs to run
    def set_procedure_loop_count(self, new_loop_count):
        if self.started.is_set():
            self.logger.error("Cannot change loop count until procedure stops")
            return
        
        
        self.loop_count = new_loop_count
        
class Timer():
    def __init__(self):
        self.start_time = None
        self.pause_time = 0
        self.is_paused = False
        
    def start(self):
        self.start_time = datetime.now()
        self.is_paused = False
        
    def pause(self):
        if self.is_paused:
            return
            
        self.pause_time = datetime.now()
        self.is_paused = True
    
    def unpause(self):
        if not self.is_paused:
            return
        
        last_pause_time = datetime.now() - self.pause_time
        self.start_time = self.start_time + last_pause_time
        self.is_paused = False
        
    def get_time(self):
        if self.start_time is None:
            return timedelta(0)
        
        if self.is_paused:
            return self.pause_time.replace(microsecond=0) - self.start_time.replace(microsecond=0)
        else:
            return datetime.now().replace(microsecond=0) - self.start_time.replace(microsecond=0)
        
    def get_current_step_index(self):
        return self.current_step

    def has_error(self):
        return self.error_flag

    def get_error_step_index(self):
        return self.error_step_index
        
