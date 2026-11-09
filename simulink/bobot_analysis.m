% BOBOT_ANALYSIS  Linear model, control-law analysis and graphs for BO-BOT.
%
% Does the same calculation as python/bobot_linear_model.py (so the two can be compared) and
% saves the figures in results_matlab/. Needs MATLAB with the Control System Toolbox.
% Equations are derived in docs/equations.md.
%
%   state  x = [v; phi; phid]   v: axle speed (m/s), phi: body angle from the balance point (rad)
clear; clc; close all;
bobot_params;
if ~exist('results_matlab','dir'), mkdir('results_matlab'); end
d2r = pi/180;  s2d = 1/d2r;

%% 1. Plant (small-angle model with DC-motor drive)
M00 = 2*Iwa/r^2 + mb + 2*mw + 2*Jm/r^2;
M01 = l*mb - 2*Jm/r;
M11 = Iyy + e^2*mb + l^2*mb + 2*Jm;
Mm  = [M00 M01; M01 M11];
k1  = 2*eta*gear*Ke/R;                 % N m per volt, both wheels at standstill
ke  = gear*Ke;                         % back-EMF constant at the wheel, V s/rad
% total drive torque:  Tt = a_v*v + a_p*phid + b_u*u      (u = duty -1..1)
a_v = -k1*ke/r;   a_p = k1*ke;   b_u = k1*Vb;
Fv   = [a_v/r; -a_v];  Fp = [a_p/r; -a_p];  Fphi = [0; g*mb*l];  Fu = [b_u/r; -b_u];
Mi = inv(Mm);
av = Mi*Fv;  aphi = Mi*Fphi;  ap = Mi*Fp;  bu = Mi*Fu;
A = [av(1)  aphi(1)  ap(1);
     0      0        1;
     av(2)  aphi(2)  ap(2)];
B = [bu(1); 0; bu(2)];
fprintf('Open-loop poles:\n'); disp(eig(A));

%% 2. Controller and closed loop (same law as the firmware)
emf = ke/r;                            % V per m/s
% z = [v phi phid xi vhat],  xi' = vcmd - vhat,  vhat = speed estimate (lag tau_v)
Aa = zeros(5);  Aa(1:3,1:3) = A;  Aa(4,5) = -1;  Aa(5,1) = 1/tau_v;  Aa(5,5) = -1/tau_v;
Ba = [B; 0; 0];
Bv = [0;0;0;1;0];
[Acl, Bcl, Kz, Kv] = bobot_closed(Aa, Ba, Bv, kp, kd, kp_v, ki_v, s2d, kff, emf, Vb, Td);
fprintf('Closed-loop poles (with %.1f ms delay):\n', Td*1e3); disp(eig(Acl));

% Self-check against the verified Python calculation (python/bobot_linear_model.py)
fprintf('\nSELF-CHECK (compares with the Python results):\n');
nfail = 0;
nfail = nfail + chk('open-loop poles', sort(real(eig(A))), [-29.961; -9.384; 10.564], 0.05, 0);
nfail = nfail + chk('closed-loop poles', sort(real(eig(Acl))), [-504.16; -90.93; -8.235; -8.235; -1.420; -0.0665], 0.01, 0.02);

%% 3. Figure 1: pole maps
p0 = eig(A);  p1 = eig(Acl);
figure('Position',[100 100 900 360]);
subplot(1,2,1); plot(real(p0), imag(p0), 'x', 'MarkerSize', 10, 'LineWidth', 2); grid on; xline(0); yline(0);
title('Open-loop poles'); xlabel('real (1/s)'); ylabel('imaginary (rad/s)');
subplot(1,2,2); plot(real(p1), imag(p1), 'x', 'MarkerSize', 10, 'LineWidth', 2); grid on; xline(0); yline(0);
title('Closed-loop poles (firmware gains)'); xlabel('real (1/s)');
saveas(gcf, 'results_matlab/01_poles.png');

%% 4. Figure 2: recovery from a 3 degree tilt, against the nonlinear simulator
T = readtable('data/sim_initial_tilt.csv');
ss = mean(T.pitch_deg(end-99:end));
x0 = [0; (T.pitch_deg(1)-ss)*d2r; 0; 0; 0; 0];
sysCl = ss_obj(Acl, Bcl);
[~, ~, xl] = lsim(sysCl, zeros(size(T.t_s)), T.t_s, x0);
figure('Position',[100 100 700 520]);
subplot(2,1,1); plot(T.t_s, T.pitch_deg-ss, 'LineWidth', 1.6); hold on; plot(T.t_s, xl(:,2)*s2d, '--', 'LineWidth', 1.6);
grid on; ylabel('pitch from rest (deg)'); legend('nonlinear simulator','linear model');
title('Recovery from a 3 degree tilt');
subplot(2,1,2); plot(T.t_s, T.speed_mps, 'LineWidth', 1.6); hold on; plot(T.t_s, xl(:,1), '--', 'LineWidth', 1.6);
grid on; ylabel('speed (m/s)'); xlabel('time (s)');
saveas(gcf, 'results_matlab/02_tilt_recovery_validation.png');

%% 5. Figure 3: speed command, ramped at 0.6 m/s per second
t2 = linspace(0, 4, 800)';
vc = min(0.2, v_ramp*t2);
[~, ~, xs] = lsim(sysCl, vc, t2, zeros(6,1));
u_duty = xs(:,1:5)*Kz' + Kv*vc;
S2 = readtable('data/sim_speed_step.csv');
figure('Position',[100 100 700 640]);
subplot(3,1,1); plot(t2, vc, 'Color', [.5 .5 .5]); hold on; plot(t2, xs(:,1), '--', 'LineWidth', 1.6); plot(S2.t_s, S2.speed_mps, 'LineWidth', 1.4);
grid on; ylabel('speed (m/s)'); legend('command','linear model','nonlinear simulator','Location','southeast');
subplot(3,1,2); plot(t2, xs(:,2)*s2d, '--', 'LineWidth', 1.6); hold on; plot(S2.t_s, S2.pitch_deg-S2.pitch_deg(1), 'LineWidth', 1.4);
grid on; ylabel('pitch change (deg)');
subplot(3,1,3); plot(t2, u_duty*255, '--', 'LineWidth', 1.6); grid on; ylabel('PWM (of 255)'); xlabel('time (s)');
saveas(gcf, 'results_matlab/03_speed_step.png');

%% 6. Figure 4: Bode plot of the angle loop (kp, kd) opened at the motor input
Kang = [kp*s2d/255, kd*s2d/255];
w = logspace(0, 3, 2000);
G = zeros(size(w));
for i = 1:numel(w)
    xi_ = (1j*w(i)*eye(3) - A) \ B;
    G(i) = -(Kang*xi_(2:3));
end
Ld = G.*exp(-1j*w*Td);
figure('Position',[100 100 700 520]);
subplot(2,1,1); semilogx(w, 20*log10(abs(G)), 'LineWidth', 1.6); grid on; yline(0); ylabel('magnitude (dB)');
subplot(2,1,2); semilogx(w, unwrap(angle(G))*s2d, 'LineWidth', 1.6); hold on; semilogx(w, unwrap(angle(Ld))*s2d, 'LineWidth', 1.6);
grid on; yline(-180); ylabel('phase (deg)'); xlabel('frequency (rad/s)'); legend('no delay', sprintf('%.1f ms delay', Td*1e3));
i0 = find(abs(G(1:end-1))>1 & abs(G(2:end))<=1, 1);
if ~isempty(i0), fprintf('Angle loop: crossover %.0f rad/s, phase margin %.0f deg (no delay), %.0f deg with delay\n', ...
        w(i0), 180+unwrap(angle(G(i0)))*s2d, 180+unwrap(angle(Ld(i0)))*s2d); end
saveas(gcf, 'results_matlab/04_angle_loop_bode.png');
if ~isempty(i0)
    nfail = nfail + chk('phase margin, no delay (deg)', 180+unwrap(angle(G(i0)))*s2d, 46.3, 1.0, 0);
    nfail = nfail + chk('phase margin, with delay (deg)', 180+unwrap(angle(Ld(i0)))*s2d, 31.8, 1.0, 0);
end

%% 7. Figure 5: gain sweeps
kps = 0:0.5:150;  P = zeros(numel(kps), 6);
for i = 1:numel(kps)
    P(i,:) = eig(bobot_closed(Aa, Ba, Bv, kps(i), kd, kp_v, ki_v, s2d, kff, emf, Vb, Td)).';
end
stable = all(real(P) < 0, 2);
fprintf('Stable for kp from %.1f to %.1f (kd = %.2f)\n', kps(find(stable,1,'first')), kps(find(stable,1,'last')), kd);
figure('Position',[100 100 900 380]);
subplot(1,2,1); scatter(real(P(:)), imag(P(:)), 6, repmat(kps(:), 6, 1), 'filled'); grid on; xline(0);
xlim([-60 10]); xlabel('real (1/s)'); ylabel('imaginary (rad/s)'); title('Closed-loop poles, kp from 0 to 150'); colorbar;
kds = 0:0.005:1.2;  mx = zeros(size(kds));
for i = 1:numel(kds)
    mx(i) = max(real(eig(bobot_closed(Aa, Ba, Bv, kp, kds(i), kp_v, ki_v, s2d, kff, emf, Vb, Td))));
end
subplot(1,2,2); plot(kds, mx, 'LineWidth', 1.6); grid on; yline(0); xline(kd, '--r'); ylim([-1 3]);
xlabel('kd'); ylabel('largest real part of any pole (1/s)'); title('Stability against kd (kp = 55)');
saveas(gcf, 'results_matlab/05_gain_sweeps.png');
nfail = nfail + chk('smallest stable kp', kps(find(stable,1,'first')), 16.5, 1.0, 0);
nfail = nfail + chk('largest stable kp', kps(find(stable,1,'last')), 121, 1.5, 0);

%% 8. Figure 6: battery voltage
figure('Position',[100 100 600 400]); hold on;
for Vbi = [8.4 7.4 6.8]
    pb = eig(bobot_closed(Aa, Ba*Vbi/Vb, Bv, kp, kd, kp_v, ki_v, s2d, kff, emf, Vb, Td));
    plot(real(pb), imag(pb), 'x', 'MarkerSize', 9, 'LineWidth', 2, 'DisplayName', sprintf('%.1f V', Vbi));
end
grid on; xline(0); legend; xlabel('real (1/s)'); ylabel('imaginary (rad/s)'); title('Closed-loop poles as the battery runs down');
saveas(gcf, 'results_matlab/06_battery_sensitivity.png');

%% 9. Figure 7: nonlinear model (ode45)
figure('Position',[100 100 700 400]); hold on;
tt = linspace(0, 2.5, 1000)';
cols = lines(3);  k = 0;
for th0 = [3 8 14]
    k = k + 1;
    z0 = [0; th0*d2r - e/l; 0; 0; 0; 0];
    opts = odeset('MaxStep', 0.002, 'RelTol', 1e-6, 'AbsTol', 1e-8);
    [tn, zn] = ode45(@(t, z) bobot_nonlinear(t, z, 0, struct('mb',mb,'l',l,'e',e,'Iyy',Iyy,'Iwa',Iwa,'mw',mw,'Jm',Jm,'r',r,'g',g,'k1',k1,'ke',ke,'Vb',Vb, ...
        'kp',kp,'kd',kd,'kp_v',kp_v,'ki_v',ki_v,'kff',kff,'emf',emf,'tau_v',tau_v,'Td',Td,'cap',pwm_cap,'max_lean',max_lean)), [0 2.5], z0, opts);
    plot(tn, (zn(:,2) + e/l)*s2d, 'Color', cols(k,:), 'LineWidth', 1.6, 'DisplayName', sprintf('nonlinear, start %d deg', th0));
    xl_ = lsim(sysCl, zeros(size(tt)), tt, [0; th0*d2r; 0; 0; 0; 0]);
    plot(tt, xl_(:,2)*s2d, ':', 'Color', cols(k,:), 'LineWidth', 1.3, 'HandleVisibility', 'off');
end
grid on; legend; xlabel('time (s)'); ylabel('angle from balance point (deg)'); title('Solid: nonlinear model. Dotted: linear model');
saveas(gcf, 'results_matlab/07_nonlinear_recovery.png');
if nfail == 0
    fprintf('\nSELF-CHECK PASSED: the MATLAB results agree with the Python results.\n');
else
    fprintf('\nSELF-CHECK: %d item(s) differ. Send me the output above so I can find the cause.\n', nfail);
end
fprintf('Done. Figures are in results_matlab/.\n');

%% ---- local functions ----
function bad = chk(name, got, want, abs_tol, rel_tol)
% PASS when every value is within abs_tol + rel_tol*|want| of the Python result.
    if numel(got) ~= numel(want)
        ok = false;
    else
        ok = all(abs(got(:) - want(:)) <= abs_tol + rel_tol*abs(want(:)));
    end
    if ok, fprintf('  PASS  %s\n', name); bad = 0; else, fprintf('  FAIL  %s\n', name); bad = 1; end
end

function sys = ss_obj(A, B)
    sys = ss(A, B, eye(size(A,1)), zeros(size(A,1), size(B,2)));
end
