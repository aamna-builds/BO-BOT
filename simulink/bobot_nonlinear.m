function dz = bobot_nonlinear(~, z, vcmd, P)
% BOBOT_NONLINEAR  Planar nonlinear model (no small-angle step) with the same controller, saturation and delay.
%   z = [v; theta; thetad; xi; vhat; xd].  theta is the body angle from vertical; the controller sees
%   phi = theta + e/l (the angle from the balance point). P is a struct of parameters.
v = z(1); th = z(2); thd = z(3); xi = z(4); vh = z(5); xd = z(6);
s2d = 180/pi;
phi = th + P.e/P.l;
target = min(max(P.kp_v*(vcmd - vh) + P.ki_v*xi, -P.max_lean), P.max_lean);
pwm = P.kp*(phi*s2d - target) + P.kd*thd*s2d + P.kff*vcmd*P.emf/P.Vb*255;
u   = min(max(pwm, -P.cap), P.cap)/255;
ya  = 2*xd - u;                                     % delayed control (Pade)
Tt  = P.k1*P.Vb*ya - P.k1*P.ke*v/P.r + P.k1*P.ke*thd;
M00 = 2*P.Iwa/P.r^2 + P.mb + 2*P.mw + 2*P.Jm/P.r^2;
m01 = cos(th)*P.l*P.mb - P.e*P.mb*sin(th) - 2*P.Jm/P.r;
M11 = P.Iyy + P.e^2*P.mb + P.l^2*P.mb + 2*P.Jm;
f   = [Tt/P.r + thd^2*(cos(th)*P.e + P.l*sin(th))*P.mb;
       -Tt + cos(th)*P.e*P.g*P.mb + P.g*P.l*P.mb*sin(th)];
acc = [M00 m01; m01 M11] \ f;
dz  = [acc(1); thd; acc(2); vcmd - vh; (v - vh)/P.tau_v; (2/P.Td)*(u - xd)];
end
