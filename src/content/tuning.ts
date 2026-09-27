import { z } from 'zod';
import { parse, stringify } from 'yaml';
import tuningYaml from '../../content/tuning.yaml?raw';

const num = z.number();

const TuningSchema = z.object({
  movement: z.object({
    runSpeed: num, minWalkSpeed: num, groundAccel: num, groundDecel: num, airAccel: num, airMaxSpeed: num,
    gravity: num, fallGravityScale: num, jumpHeight: num, minJumpHeight: num, coyoteTime: num, jumpBuffer: num,
    terminalFall: num, turnSpeed: num, dashSpeed: num, dashTime: num, dashInvuln: num, dashCooldown: num,
    dashJumpSpeed: num, strafeSpeed: num,
  }),
  camera: z.object({
    distance: num, minDistance: num, pivotHeight: num, fov: num, sensitivityX: num, sensitivityY: num,
    minPitch: num, maxPitch: num, defaultPitch: num, autoRecenterDelay: num, autoRecenterSpeed: num, lockOnYawSpeed: num,
  }),
  lockOn: z.object({
    range: num, loseRange: num, loseSightTime: num, centerWeight: num, distanceWeight: num, homingDegPerSec: num, scanTime: num,
  }),
  gun: z.object({
    damage: num, rate: num, range: num, speed: num, chargeLv1Time: num, chargeLv2Time: num,
    chargeLv1Mult: num, chargeLv2Mult: num, chargeMoveScale: num, tapRate: num,
  }),
  sword: z.object({
    combo: z.array(num).length(3), comboTimes: z.array(num).length(3), comboStep: num, range: num, arcDeg: num,
    inputBuffer: num, airSlash: num, airSlashMax: num, airHangTime: num, dashSlash: num, lunge: num, lungeMin: num,
    lungeMax: num, lungeSpeed: num, chargeTime: num, chargeSlash: num, shockwave: num, shockwaveRange: num,
    hitstop: num, hitstopFinisher: num, hitstopCharge: num,
  }),
  drill: z.object({ damagePerTick: num, tickInterval: num, energyPerSec: num, range: num }),
  player: z.object({ maxHp: num, hurtInvuln: num, healAmount: num }),
  enemies: z.object({
    maxAttackers: num,
    sentry: z.object({
      hp: num, shotDamage: num, shotSpeed: num, keepDistance: z.tuple([num, num]), burstCount: num,
      burstInterval: num, windup: num, cooldown: num, moveSpeed: num, sight: num, poise: num,
    }),
    charger: z.object({
      hp: num, damage: num, windup: num, chargeSpeed: num, chargeTime: num, stunTime: num, recover: num,
      moveSpeed: num, sight: num, poise: num,
    }),
  }),
});

export type Tuning = z.infer<typeof TuningSchema>;

/** 既定の数値を読み込む。呼ぶたびに新しいオブジェクトを返す（調整パネルが書き換えても元は変わらない） */
export function loadTuning(): Tuning {
  return TuningSchema.parse(parse(tuningYaml));
}

export function tuningToYaml(t: Tuning): string {
  return stringify(t, { flowCollectionPadding: false });
}
