% BUILD_BOBOT_MODEL  Builds the Simulink model bobot_balance.slx (linear plant + the firmware control law).
%
% Run this script in MATLAB. It builds the model, runs it, saves bobot_balance.slx plus a picture of the
% block diagram and the result graphs in results_matlab/. You can also open bobot_balance.slx and press Run.
% The block diagram follows the firmware: speed estimate lag,
% outer speed PI loop giving a lean target, inner angle PD loop, back-EMF feed-forward, PWM limit
% and the control delay.
%
% Signals logged to the workspace (timeseries): out_v (speed), out_phi (pitch, rad), out_duty (motor duty).
clear; clc;
bobot_params;
d2r = pi/180;  s2d = 1/d2r;

%% plant matrices (same as bobot_analysis.m)
M00 = 2*Iwa/r^2 + mb + 2*mw + 2*Jm/r^2;
M01 = l*mb - 2*Jm/r;
M11 = Iyy + e^2*mb + l^2*mb + 2*Jm;
Mi  = inv([M00 M01; M01 M11]);
k1  = 2*eta*gear*Ke/R;   ke = gear*Ke;   emf = ke/r;
a_v = -k1*ke/r;  a_p = k1*ke;  b_u = k1*Vb;
av = Mi*[a_v/r; -a_v];  aphi = Mi*[0; g*mb*l];  ap = Mi*[a_p/r; -a_p];  bu = Mi*[b_u/r; -b_u];
A = [av(1) aphi(1) ap(1); 0 0 1; av(2) aphi(2) ap(2)];
B = [bu(1); 0; bu(2)];
x0 = [0; 3*d2r; 0];                    % start 3 degrees off the balance point

%% model
mdl = 'bobot_balance';
if bdIsLoaded(mdl), close_system(mdl, 0); end
new_system(mdl); open_system(mdl);
set_param(mdl, 'Solver', 'ode45', 'MaxStep', '0.001', 'StopTime', '5');

add = @(src, name, pos, varargin) add_block(src, [mdl '/' name], 'Position', pos, varargin{:});

% command: step in speed, limited to 0.6 m/s per second like the firmware
add('simulink/Sources/Step',            'vcmd_step', [20 100 60 130], 'Time', '0.5', 'Before', '0', 'After', '0.2');
add('simulink/Discontinuities/Rate Limiter', 'vcmd', [90 100 150 130], 'RisingSlewLimit', 'v_ramp', 'FallingSlewLimit', '-v_ramp');

% plant: states [v; phi; phid]
add('simulink/Continuous/State-Space',  'Plant', [900 200 1000 280], 'A', 'A', 'B', 'B', 'C', 'eye(3)', 'D', 'zeros(3,1)', 'X0', 'x0');
add('simulink/Signal Routing/Demux',    'split', [1030 190 1035 290], 'Outputs', '3');

% speed estimate (lag) and speed error
add('simulink/Continuous/Transfer Fcn', 'speed_est', [1080 120 1160 160], 'Numerator', '[1]', 'Denominator', '[tau_v 1]');
add('simulink/Math Operations/Sum',     'speed_err', [200 100 230 130], 'Inputs', '+-');
add('simulink/Math Operations/Gain',    'kp_v',  [280 60 330 90],  'Gain', 'kp_v');
add('simulink/Continuous/Integrator',   'int_err', [260 140 290 170]);
add('simulink/Math Operations/Gain',    'ki_v',  [320 140 370 170], 'Gain', 'ki_v');
add('simulink/Math Operations/Sum',     'lean_sum', [400 90 430 130], 'Inputs', '++');
add('simulink/Discontinuities/Saturation', 'lean_limit', [450 95 500 125], 'UpperLimit', 'max_lean', 'LowerLimit', '-max_lean');

% angle loop: phi (deg) - target, then kp, kd on the pitch rate
add('simulink/Math Operations/Gain',    'rad2deg_phi', [1080 200 1130 230], 'Gain', 's2d');
add('simulink/Math Operations/Gain',    'rad2deg_rate', [1080 250 1130 280], 'Gain', 's2d');
add('simulink/Math Operations/Sum',     'angle_err', [540 180 570 210], 'Inputs', '+-');
add('simulink/Math Operations/Gain',    'kp',    [600 180 650 210], 'Gain', 'kp');
add('simulink/Math Operations/Gain',    'kd',    [600 240 650 270], 'Gain', 'kd');
add('simulink/Math Operations/Sum',     'pwm_sum', [690 190 720 250], 'Inputs', '+++');
add('simulink/Math Operations/Gain',    'ff',    [280 330 330 360], 'Gain', 'kff*emf/Vb*255');

% PWM limit (80 %), scale to duty, delay, back to the plant
add('simulink/Discontinuities/Saturation', 'pwm_limit', [750 190 800 250], 'UpperLimit', 'pwm_cap', 'LowerLimit', '-pwm_cap');
add('simulink/Math Operations/Gain',    'to_duty', [820 200 870 230], 'Gain', '1/255');
add('simulink/Continuous/Transport Delay', 'control_delay', [820 280 880 310], 'DelayTime', 'Td');

% logging and scopes
add('simulink/Sinks/To Workspace', 'log_v',    [1200 200 1260 220], 'VariableName', 'out_v',    'SaveFormat', 'Timeseries');
add('simulink/Sinks/To Workspace', 'log_phi',  [1200 230 1260 250], 'VariableName', 'out_phi',  'SaveFormat', 'Timeseries');
add('simulink/Sinks/To Workspace', 'log_duty', [900 330 960 350],   'VariableName', 'out_duty', 'SaveFormat', 'Timeseries');
add('simulink/Sinks/Scope', 'scope_speed', [1200 100 1240 140], 'NumInputPorts', '2');
add('simulink/Sinks/Scope', 'scope_pitch', [1200 280 1240 320]);

% Wiring. The Plant output is a 3-vector [v; phi; phid].
ln = @(a, b) add_line(mdl, a, b, 'autorouting', 'on');
ln('vcmd_step/1', 'vcmd/1');
ln('vcmd/1',      'speed_err/1');
ln('speed_err/1', 'kp_v/1');
ln('speed_err/1', 'int_err/1');
ln('int_err/1',   'ki_v/1');
ln('kp_v/1',      'lean_sum/1');
ln('ki_v/1',      'lean_sum/2');
ln('lean_sum/1',  'lean_limit/1');
ln('lean_limit/1','angle_err/2');
ln('rad2deg_phi/1','angle_err/1');
ln('angle_err/1', 'kp/1');
ln('rad2deg_rate/1','kd/1');
ln('kp/1',        'pwm_sum/1');
ln('kd/1',        'pwm_sum/2');
ln('vcmd/1',      'ff/1');
ln('ff/1',        'pwm_sum/3');
ln('pwm_sum/1',   'pwm_limit/1');
ln('pwm_limit/1', 'to_duty/1');
ln('to_duty/1',   'control_delay/1');
ln('control_delay/1', 'Plant/1');
ln('to_duty/1',   'log_duty/1');
ln('Plant/1',     'split/1');
ln('split/1',     'speed_est/1');
ln('speed_est/1', 'speed_err/2');
ln('split/2',     'rad2deg_phi/1');
ln('split/3',     'rad2deg_rate/1');
ln('split/1',     'log_v/1');
ln('split/2',     'log_phi/1');
ln('vcmd/1',      'scope_speed/1');
ln('split/1',     'scope_speed/2');
ln('split/2',     'scope_pitch/1');

% tidy the layout (optional, needs R2016a or newer)
try
    Simulink.BlockDiagram.arrangeSystem(mdl);
catch
    fprintf('Note: could not auto-arrange the blocks; move them by hand if the layout looks crowded.\n');
end

here = fileparts(mfilename('fullpath'));
if ~exist(fullfile(here,'results_matlab'),'dir'), mkdir(fullfile(here,'results_matlab')); end
save_system(mdl, fullfile(here, [mdl '.slx']));
fprintf('Saved %s.slx\n', mdl);

% picture of the block diagram for the README
try
    print(['-s' mdl], '-dpng', '-r150', fullfile(here, 'results_matlab', 'bobot_balance_model.png'));
    fprintf('Saved results_matlab/bobot_balance_model.png\n');
catch
    fprintf('Note: could not export the model picture. In Simulink, use File > Print > Export, or take a screenshot.\n');
end

%% run it and plot
simOut = sim(mdl, 'ReturnWorkspaceOutputs', 'on');
v   = simOut.get('out_v');     phi = simOut.get('out_phi');     duty = simOut.get('out_duty');
figure('Position', [100 100 760 640]);
subplot(3,1,1); plot(v.Time, v.Data, 'LineWidth', 1.6); grid on; ylabel('speed (m/s)'); title('bobot\_balance: start 3 deg off, speed command 0.2 m/s at 0.5 s');
subplot(3,1,2); plot(phi.Time, phi.Data*s2d, 'LineWidth', 1.6); grid on; ylabel('pitch from balance point (deg)');
subplot(3,1,3); plot(duty.Time, duty.Data*255, 'LineWidth', 1.6); grid on; ylabel('PWM (of 255)'); xlabel('time (s)');
saveas(gcf, fullfile(here, 'results_matlab', 'bobot_balance_simulink_results.png'));

% quick sanity checks (the Python model gives about 0.2 m/s and a pitch that settles to 0 within 2 s of the command)
v_end = v.Data(end);  phi_end = phi.Data(end)*s2d;
fprintf('\nSIMULINK CHECK\n');
if abs(v_end - 0.2) < 0.02, fprintf('  PASS  final speed %.3f m/s (expected about 0.2)\n', v_end); else, fprintf('  FAIL  final speed %.3f m/s (expected about 0.2)\n', v_end); end
if abs(phi_end) < 0.5,      fprintf('  PASS  final pitch %.2f deg (expected about 0)\n', phi_end); else, fprintf('  FAIL  final pitch %.2f deg (expected about 0)\n', phi_end); end
if max(abs(phi.Data))*s2d < 6, fprintf('  PASS  pitch stays within 6 deg\n'); else, fprintf('  FAIL  pitch went beyond 6 deg\n'); end
fprintf('Done. Open %s.slx to see the model, and results_matlab/ for the pictures.\n', mdl);
