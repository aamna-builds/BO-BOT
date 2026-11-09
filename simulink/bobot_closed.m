function [Ac, Bc, Kz, Kv] = bobot_closed(Aa, Ba, Bv, kp, kd, kpv, kiv, s2d, kff, emf, Vb, Td)
% BOBOT_CLOSED  Closed-loop matrices of the balance robot with the firmware control law.
%   Plant states z = [v phi phid xi vhat]; the control delay Td is added as a first-order Pade
%   element (y = 2*xd - u, xd' = (2/Td)(u - xd)), so the result has 6 states: [z; xd]. Input: vcmd.
%   duty u = Kz*z + Kv*vcmd.
Kz = [0, kp*s2d/255, kd*s2d/255, -kp*kiv/255, kp*kpv/255];
Kv = -kp*kpv/255 + kff*emf/Vb;
Ac = zeros(6);  Bc = zeros(6,1);
Ac(1:5,1:5) = Aa - Ba*Kz;   Ac(1:5,6) = 2*Ba;
Ac(6,1:5)   = (2/Td)*Kz;    Ac(6,6)   = -2/Td;
Bc(1:5)     = Bv - Ba*Kv;   Bc(6)     = (2/Td)*Kv;
end
