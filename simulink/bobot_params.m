% BOBOT_PARAMS  Physical and controller parameters of BO-BOT (no shell).
%
% Same numbers as the web simulator (simulation/web/index.html) and the firmware
% (firmware/balance_bot/include/controller.h). Run this first; the other scripts call it.
% Units: SI, angles in radians unless a name ends in _deg.

g  = 9.81;                      % gravity, m/s^2

% --- body and wheels
mb  = 0.1925;                   % body mass (no shell), kg
mw  = 0.0032;                   % mass of one wheel, kg
l   = 0.023733506;              % centre of mass above the axle, m
e   = 0.000301299;              % centre of mass ahead of the axle, m
Iyy = 1.12044568e-4;            % body pitch inertia about its centre of mass, kg m^2
r   = 0.017;                    % wheel radius, m
track = 0.078;                  % wheel spacing, m (simulator value; CAD says 70 mm, measure the robot)
Iwa = 4.964e-7;                 % wheel inertia about its axle, kg m^2

% --- motor GA12-N20, 6 V, 300 rpm, 50:1 gearbox
gear = 50;
R    = 6.0/0.55;                % winding resistance from stall current 0.55 A, ohm
w_nl = 300*gear*2*pi/60;        % no-load speed of the motor shaft (300 rpm at the output x 50), rad/s
Ke   = (6.0 - 0.04*R)/w_nl;     % back-EMF constant at the motor shaft, V s/rad (= torque constant, Nm/A): (V - I0*R) / no-load speed
eta  = 0.7047695986;            % gearbox efficiency, from stall torque 0.70 kg cm
Jm   = 2.5e-8*gear^2;           % rotor inertia reflected to the wheel, kg m^2
Vb   = 8.3;                     % battery voltage, V (2S, about 95 % charged)

% --- firmware control law (controller.h)
kp = 55;  kd = 0.35;  ki = 0;   % PWM counts per degree, per deg/s
kp_v = 20; ki_v = 0.9;          % degrees of lean per m/s, per metre
kff  = 1.0;
pwm_cap  = 204;                 % 80 % of 255
max_lean = 10;                  % degrees
tau_v = 0.0217;                 % speed estimate: 5-sample average (10 ms) + 0.3 low-pass (11.7 ms), s
Td    = 0.0035;                 % control delay: 1 ms output delay + half of the 5 ms sample, s
v_ramp = 0.6;                   % speed command ramp, m/s per s
