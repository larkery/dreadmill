#include "Arduino.h"

unsigned long speed_adjustment_interval = 256;

const short pulse = 825; // one cycle, roughly
//const unsigned int signal_interval = 50*pulse;
const static unsigned char max_speed = 192;

//#define DEBUG_BITWISE

byte command, s1, s2, checksum;

void isr_set_speed(void) {
  Serial.write(0x68);
  Serial.write(0x08);
  Serial.write(0x20);
  Serial.write(command);
  Serial.write(s1);
  Serial.write(s2);
  Serial.write((byte)0x0);
  Serial.write(0x14);
  Serial.write(checksum);
  Serial.write(0x43);
}

class Controller {
public:
  void begin() {
    set_current_speed(0);
    target_speed = 0;
    next_signal_time = next_speed_adjustment_time = 0;
    speed_just_changed = true;
    stable_speed = 0;
    Timer1.initialize();
    Timer1.attachInterrupt(isr_set_speed, 120000);
  }
  void tick() {
    speed_just_changed = false;

    //    // Emit pulse train for control purposes
    //    unsigned long time_now = micros();
    //    if ((time_now >= next_signal_time) ||
    //      ((next_signal_time - time_now) > signal_interval))
    //    {

    //      next_signal_time = micros() + signal_interval;
    //    }

    // consider speed adjustment
    unsigned long  time_now = millis();
    if (target_speed != current_speed) {
      if ((time_now >= next_speed_adjustment_time) ||
        ((next_speed_adjustment_time - time_now) > speed_adjustment_interval))
      {
        if (target_speed > current_speed) {
          set_current_speed(current_speed + 1);
        }
        if (target_speed < current_speed) {
          set_current_speed(current_speed - 1);
        }
        debug.write((byte)254);
        debug.write('L');
        debug.write((byte) 2);
        debug.write((byte)254);
        debug.write('b');
        debug.write((byte)16);
        debug.write((byte) ((100 * (current_speed-stable_speed)) / (target_speed - stable_speed)));
        if (target_speed == current_speed) {
          stable_speed = current_speed;
          next_speed_adjustment_time = 0;
        } 
        else {
          next_speed_adjustment_time = millis() + speed_adjustment_interval;
        }
      }
    }
  }
  void set_target_speed(unsigned char new_speed) {
    if (new_speed > max_speed) {
      target_speed = max_speed;
    } 
    else {
      target_speed = new_speed;
    }
  }
  void increase_speed() {
    if (target_speed == max_speed) return;
    target_speed++;
  }
  void decrease_speed() {
    if (target_speed == 0) return;
    target_speed--;
  }

  byte get_current_speed() {
    return current_speed;
  }

  byte get_target_speed() {
    return target_speed;
  }

  boolean has_speed_just_changed() {
    return speed_just_changed;
  }

private:
  void set_current_speed(unsigned char new_speed) {
    if (new_speed > max_speed) return;
    speed_just_changed = true;

    current_speed = new_speed;
    Timer1.stop();
    if (current_speed == 0) {
      command = s1 = s2 = 0x0;
    } 
    else {
      command = 0x50;
      int s = 0xE1 + (current_speed-1) * 0x16;
      s1 = (s >> 8);
      s2 = 0;
      s2 |= s;
    }

    checksum = 0;
    checksum += 0x08;
    checksum += 0x20;
    checksum += command;
    checksum += s1;
    checksum += s2;
    checksum += 0x14;
    Timer1.resume();
  }

  boolean speed_just_changed;
  unsigned int control_pin;
  unsigned char target_speed;
  unsigned char current_speed;
  unsigned char stable_speed;
  unsigned long next_signal_time;
  unsigned long next_speed_adjustment_time;
};







