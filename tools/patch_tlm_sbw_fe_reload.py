from pathlib import Path

path = Path("tlm/src/main/java/com/github/tartaricacid/touhoulittlemaid/compat/gun/swarfare/SWarfareCompatInner.java")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "import net.neoforged.neoforge.network.PacketDistributor;\n",
    "import net.neoforged.neoforge.capabilities.Capabilities;\n"
    "import net.neoforged.neoforge.energy.IEnergyStorage;\n"
    "import net.neoforged.neoforge.items.IItemHandler;\n"
    "import net.neoforged.neoforge.network.PacketDistributor;\n",
)

old = """        // 先尝试装填弹药
        int result = doGunReload(shooter, gunData);
"""
new = """        // FE weapons use the gun stack itself as their ammo store. A maid cannot
        // interact with a charging station while fighting, so transfer energy from
        // any extractable FE item in the maid inventory before normal reload logic.
        if (!gunData.canShoot(shooter) && chargeEnergyGun(shooter, gunItem)) {
            MaidAnimationPackage msg = new MaidAnimationPackage(shooter.getId(), SWF_RELOAD);
            PacketDistributor.sendToPlayersTrackingEntity(shooter, msg);
            return 5;
        }

        // 先尝试装填弹药
        int result = doGunReload(shooter, gunData);
"""
if old not in text:
    raise SystemExit("performGunAttack insertion point not found")
text = text.replace(old, new, 1)

marker = """    private static int doGunReload(EntityMaid shooter, GunData gunData) {
"""
helper = """    /**
     * Charges an FE-backed Superb Warfare gun from energy items carried by the maid.
     *
     * <p>Superb Warfare models FE guns as magazine-less weapons whose ammo is the
     * energy capability attached to the gun ItemStack. Therefore the ordinary
     * {@code shouldStartReloading} path intentionally never runs for them.</p>
     */
    private static boolean chargeEnergyGun(EntityMaid shooter, ItemStack gunItem) {
        IEnergyStorage gunEnergy = gunItem.getCapability(Capabilities.EnergyStorage.ITEM);
        if (gunEnergy == null || !gunEnergy.canReceive()) {
            return false;
        }

        int missing = gunEnergy.getMaxEnergyStored() - gunEnergy.getEnergyStored();
        if (missing <= 0) {
            return false;
        }

        IItemHandler inventory = shooter.getCapability(Capabilities.ItemHandler.ENTITY);
        if (inventory == null) {
            return false;
        }

        boolean transferredAny = false;
        for (int slot = 0; slot < inventory.getSlots() && missing > 0; slot++) {
            ItemStack sourceStack = inventory.getStackInSlot(slot);
            if (sourceStack.isEmpty() || sourceStack == gunItem) {
                continue;
            }

            IEnergyStorage sourceEnergy = sourceStack.getCapability(Capabilities.EnergyStorage.ITEM);
            if (sourceEnergy == null || !sourceEnergy.canExtract()) {
                continue;
            }

            int extractable = sourceEnergy.extractEnergy(missing, true);
            if (extractable <= 0) {
                continue;
            }

            int acceptable = gunEnergy.receiveEnergy(extractable, true);
            if (acceptable <= 0) {
                continue;
            }

            int extracted = sourceEnergy.extractEnergy(acceptable, false);
            int received = gunEnergy.receiveEnergy(extracted, false);
            if (received > 0) {
                transferredAny = true;
                missing -= received;
            }
        }
        return transferredAny;
    }

"""
if marker not in text:
    raise SystemExit("doGunReload marker not found")
text = text.replace(marker, helper + marker, 1)

path.write_text(text, encoding="utf-8")
print(f"Patched {path}")
