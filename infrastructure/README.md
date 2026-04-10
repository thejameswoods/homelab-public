# Infrastructure: 3-Node Proxmox Cluster

The homelab is built on a 3-node **Proxmox Virtual Environment (PVE)** cluster, providing a robust, high-availability foundation for virtualization.

## 🚀 Architectural Vision

The cluster was designed to eliminate single points of failure while maximizing hardware resources. By using multiple nodes, I can:
- Perform rolling maintenance without taking down critical services.
- Distribute workloads based on node-specific hardware (e.g., GPU-equipped node for AI).
- Ensure data integrity through a cluster-aware storage strategy.

## 🛠️ Compute Specifications

- **Hypervisor:** Proxmox VE 8.x
- **Configuration:** 3-Node High Availability (HA) Cluster
- **Workloads:** A mix of Ubuntu-based Virtual Machines (VMs) and lightweight LXC containers.

## 📦 Storage Strategy: ZFS & OMV

Data resilience is managed through a tiered storage approach:
1.  **Local ZFS Pools:** Each node utilizes ZFS for its OS and critical service storage, providing data integrity through checksumming and snapshotting.
2.  **NAS Integration:** **OpenMediaVault (OMV)** acts as the primary storage controller, managing a large redundant storage pool.
3.  **Real-Time Mirroring:** A second OMV server acts as a standby mirror, with scheduled `rsync` jobs and ZFS send/receive tasks ensuring data is duplicated across physical hardware.

## 🕒 Backup Strategy

- **Proxmox Backup Server (PBS):** All VMs and LXCs are automatically backed up to a dedicated PBS instance on a daily schedule.
- **Off-Site Backups:** Encrypted backups of critical data (photos, documents) are pushed to a remote location weekly using `rclone`.
- **Snapshot Management:** Before any major configuration change or system update, a manual snapshot is taken for immediate rollback.

## 📊 Monitoring & Health

Node health, temperature, and resource utilization are monitored via a centralized **Grafana** dashboard, pulling metrics from **InfluxDB** and **Netdata**.

---
*Back to [Top](../README.md)*
