import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { PoseOverride } from '../../src/view/characterLook';

/** 値が変わらない動作（待機の右腕など）の上で、骨を手で動かしたあとに元へ戻るか */
function setup() {
  const bone = new THREE.Bone();
  bone.name = 'arm';
  const root = new THREE.Object3D();
  root.add(bone);
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.3, 0, 0));
  const track = new THREE.QuaternionKeyframeTrack('arm.quaternion', [0, 1], [...q.toArray(), ...q.toArray()]);
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(new THREE.AnimationClip('idle', 1, [track])).play();
  return { bone, mixer, q };
}

describe('PoseOverride', () => {
  it('手で動かした骨は、後始末がないと次のフレームで戻らない（three.js の動作の確認）', () => {
    const { bone, mixer, q } = setup();
    mixer.update(1 / 60);
    bone.quaternion.setFromEuler(new THREE.Euler(-1.5, 0, 0)); // 照準で腕を上げる
    mixer.update(1 / 60);
    expect(bone.quaternion.angleTo(q)).toBeGreaterThan(0.1);
  });

  it('restore と capture で挟むと、構えをやめた次のフレームで動作の姿勢に戻る', () => {
    const { bone, mixer, q } = setup();
    const o = new PoseOverride([bone]);
    for (let i = 0; i < 3; i++) {
      o.restore();
      mixer.update(1 / 60);
      o.capture();
      bone.quaternion.setFromEuler(new THREE.Euler(-1.5, 0, 0));
    }
    // 構えをやめる
    o.restore();
    mixer.update(1 / 60);
    o.capture();
    expect(bone.quaternion.angleTo(q)).toBeLessThan(1e-6);
  });

  it('毎フレーム少しずつ回す処理（胸のひねり）が積み重ならない', () => {
    const { bone, mixer, q } = setup();
    const o = new PoseOverride([bone]);
    for (let i = 0; i < 30; i++) {
      o.restore();
      mixer.update(1 / 60);
      o.capture();
      bone.rotateY(0.2);
    }
    const expected = q.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.2));
    expect(bone.quaternion.angleTo(expected)).toBeLessThan(1e-6);
  });
});
