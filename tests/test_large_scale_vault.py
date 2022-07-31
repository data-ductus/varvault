import json
import time

from commons import *

vault_file_new = f"{DIR}/new-vault.json"
large_vault_file = f"{DIR}/large-scale-existing-vault.json"


class ResultToUploadDict(varvault.VaultStructDictBase):
    def __init__(self, **vault_pairs):
        super(ResultToUploadDict, self).__init__(**vault_pairs)
        self.nsover = vault_pairs.get("nsover")
        self.buildid = vault_pairs.get("buildid")
        self.testid = vault_pairs.get("testid")
        self.testdescr = vault_pairs.get("testdescr")
        self.starttime = vault_pairs.get("starttime")
        self.endtime = vault_pairs.get("endtime")
        self.status = vault_pairs.get("status")
        self.logpath = vault_pairs.get("logpath")

    @classmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        return ResultToUploadDict(**vault_value)


class ResultDict(ResultToUploadDict):
    def __init__(self, **vault_pairs):
        super(ResultDict, self).__init__(**vault_pairs)
        self.version_ha1 = vault_pairs.get("version_ha1")
        self.version_ha2 = vault_pairs.get("version_ha2")
        self.version_ha3 = vault_pairs.get("version_ha3")

    @classmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        return ResultDict(**vault_value)


class GroupInstallers(varvault.VaultStructDictBase):
    class Group(varvault.VaultStructDictBase):
        def __init__(self, installer, installer_upgrade=None):
            super(GroupInstallers.Group, self).__init__(installer=installer, installer_upgrade=installer_upgrade)
            self.installer = installer
            self.installer_upgrade = installer_upgrade

        @classmethod
        def build_from_vault_key(cls, vault_key, vault_value):
            return GroupInstallers.Group(**vault_value)

    def __init__(self, **vault_pairs):
        super(GroupInstallers, self).__init__(**vault_pairs)
        for group, group_data in vault_pairs.items():
            self.__setattr__(group, self.Group.build_from_vault_key(vault_key=group,
                                                                    vault_value=dict(installer=group_data.get("installer"),
                                                                                     installer_upgrade=group_data.get("installer-upgrade"))))

    @classmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        return GroupInstallers(**vault_value)


class KeyringLargeScale(varvault.Keyring):
    logname = varvault.Key("logname", valid_type=str)
    log_out_dir = varvault.Key("log_out_dir", valid_type=str)
    hostsfile_path = varvault.Key("hostsfile_path", valid_type=str)
    influxdb_ip = varvault.Key("influxdb_ip", valid_type=str)
    influxdb_port = varvault.Key("influxdb_port", valid_type=str)
    influxdb_database = varvault.Key("influxdb_database", valid_type=str)
    grafana_hostname = varvault.Key("grafana_hostname", valid_type=str)
    grafana_port = varvault.Key("grafana_port", valid_type=str)
    grafana_credentials = varvault.Key("grafana_credentials", valid_type=str)
    grafana_auth_token = varvault.Key("grafana_auth_token", valid_type=str)
    result = varvault.Key("result", valid_type=ResultDict)
    result_to_upload = varvault.Key("result_to_upload", valid_type=ResultToUploadDict)
    installer_local = varvault.Key("installer_local", valid_type=str)
    installer_local_pre_upgrade = varvault.Key("installer_local_pre_upgrade", valid_type=str)
    installer_local_post_upgrade = varvault.Key("installer_local_post_upgrade", valid_type=str)
    group_installers = varvault.Key("group_installers", valid_type=GroupInstallers)
    descriptor_file = varvault.Key("descriptor_file", valid_type=str)
    docker_network = varvault.Key("docker_network", valid_type=str)
    docker_network_existed_on_start = varvault.Key("docker_network_existed_on_start", valid_type=bool)
    cpus_per_container = varvault.Key("cpus_per_container", valid_type=int, can_be_none=True)
    target_env = varvault.Key("target_env", valid_type=str)
    workspace_dir = varvault.Key("workspace_dir", valid_type=str)
    test_time = varvault.Key("test_time", valid_type=str)
    start_time = varvault.Key("start_time", valid_type=float)
    end_time = varvault.Key("end_time", valid_type=float)
    build_id = varvault.Key("build_id", valid_type=str)
    test_id = varvault.Key("test_id", valid_type=str)
    test_description = varvault.Key("test_description", valid_type=str)
    instance_count = varvault.Key("instance_count", valid_type=str)
    container_count = varvault.Key("container_count", valid_type=str)
    version = varvault.Key("version", valid_type=str)
    branch = varvault.Key("branch", valid_type=str)
    branch_custom = varvault.Key("branch_custom", valid_type=str, can_be_none=True)
    branch_ha1 = varvault.Key("branch_ha1", valid_type=str)
    branch_ha2 = varvault.Key("branch_ha2", valid_type=str)
    branch_ha3 = varvault.Key("branch_ha3", valid_type=str)
    version_ha1 = varvault.Key("version_ha1", valid_type=str)
    version_ha2 = varvault.Key("version_ha2", valid_type=str)
    version_ha3 = varvault.Key("version_ha3", valid_type=str)
    branch_upgrade_ha1 = varvault.Key("branch_upgrade_ha1", valid_type=str)
    branch_upgrade_ha2 = varvault.Key("branch_upgrade_ha2", valid_type=str)
    branch_upgrade_ha3 = varvault.Key("branch_upgrade_ha3", valid_type=str)
    version_upgrade_ha1 = varvault.Key("version_upgrade_ha1", valid_type=str)
    version_upgrade_ha2 = varvault.Key("version_upgrade_ha2", valid_type=str)
    version_upgrade_ha3 = varvault.Key("version_upgrade_ha3", valid_type=str)
    version_pre_upgrade = varvault.Key("version_pre_upgrade", valid_type=str)
    validation_errors = varvault.Key("validation_errors", valid_type=list, can_be_none=True)
    validation_result = varvault.Key("validation_result", valid_type=dict)


class TestLargeScaleVault:

    def setup_method(self):
        try:
            os.remove(vault_file_new)
        except:
            pass

    def test_load_from_large_vault(self):
        vault = varvault.from_vault(KeyringLargeScale, "vault", varvault.JsonFilehandler(large_vault_file), varvault.VaultFlags.remove_existing_log_file(), varvault.VaultFlags.remove_existing_log_file(), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        logger.info("Created the vault from file")
        # We load from existing and write to new, so just check that the new file contains the correct data
        contents = json.load(open(vault_file_new))
        assert KeyringLargeScale.workspace_dir in contents
        assert KeyringLargeScale.test_time in contents
        assert KeyringLargeScale.cpus_per_container in contents
        assert KeyringLargeScale.docker_network in contents
        assert KeyringLargeScale.branch in contents
        assert KeyringLargeScale.descriptor_file in contents
        assert KeyringLargeScale.logname in contents
        assert KeyringLargeScale.log_out_dir in contents
        assert KeyringLargeScale.hostsfile_path in contents
        assert KeyringLargeScale.grafana_port in contents
        assert KeyringLargeScale.influxdb_database in contents
        assert KeyringLargeScale.installer_local_pre_upgrade in contents
        assert KeyringLargeScale.installer_local_post_upgrade in contents
        assert KeyringLargeScale.group_installers in contents
        assert KeyringLargeScale.branch_custom in contents
        assert KeyringLargeScale.target_env in contents
        assert KeyringLargeScale.start_time in contents
        assert KeyringLargeScale.version in contents
        assert KeyringLargeScale.version_pre_upgrade in contents
        assert KeyringLargeScale.version_ha1 in contents
        assert KeyringLargeScale.version_ha2 in contents
        assert KeyringLargeScale.version_ha3 in contents
        assert KeyringLargeScale.version_upgrade_ha1 in contents
        assert KeyringLargeScale.version_upgrade_ha2 in contents
        assert KeyringLargeScale.version_upgrade_ha3 in contents
        assert KeyringLargeScale.build_id in contents
        assert KeyringLargeScale.test_id in contents
        assert KeyringLargeScale.test_description in contents
        assert KeyringLargeScale.branch_ha1 in contents
        assert KeyringLargeScale.branch_ha2 in contents
        assert KeyringLargeScale.branch_ha3 in contents
        assert KeyringLargeScale.branch_upgrade_ha1 in contents
        assert KeyringLargeScale.branch_upgrade_ha2 in contents
        assert KeyringLargeScale.branch_upgrade_ha3 in contents
        assert KeyringLargeScale.docker_network_existed_on_start in contents
        assert KeyringLargeScale.influxdb_ip in contents
        assert KeyringLargeScale.grafana_hostname in contents
        assert KeyringLargeScale.end_time in contents
        assert KeyringLargeScale.validation_result in contents
        assert KeyringLargeScale.validation_errors in contents
        assert KeyringLargeScale.result_to_upload in contents
        assert KeyringLargeScale.result in contents

    def test_get_multiple(self):
        vault = varvault.from_vault(KeyringLargeScale, "vault", varvault.JsonFilehandler(large_vault_file), varvault.VaultFlags.remove_existing_log_file(), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        keys = [KeyringLargeScale.workspace_dir,
                KeyringLargeScale.test_time,
                KeyringLargeScale.start_time,
                KeyringLargeScale.grafana_port,
                KeyringLargeScale.group_installers,
                KeyringLargeScale.version_pre_upgrade,
                KeyringLargeScale.version_upgrade_ha1,
                KeyringLargeScale.version_upgrade_ha2,
                KeyringLargeScale.version_upgrade_ha3,
                KeyringLargeScale.result_to_upload,
                KeyringLargeScale.result,
                ]

        vars = vault.get_multiple(keys)
        # This list should be empty; If not, a key is missing in the vault
        assert len([key for key in keys if key not in vars]) == 0, f"Keys are missing in vars: {[key for key in keys if key not in vars]}"

    def test_get_via_vaulter(self):
        vault = varvault.from_vault(KeyringLargeScale, "vault", varvault.JsonFilehandler(large_vault_file), varvault.VaultFlags.remove_existing_log_file(), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        keys = [KeyringLargeScale.workspace_dir,
                KeyringLargeScale.test_time,
                KeyringLargeScale.cpus_per_container,
                KeyringLargeScale.docker_network,
                KeyringLargeScale.branch,
                KeyringLargeScale.descriptor_file,
                KeyringLargeScale.logname,
                KeyringLargeScale.log_out_dir,
                KeyringLargeScale.hostsfile_path,
                KeyringLargeScale.grafana_port,
                KeyringLargeScale.influxdb_database,
                KeyringLargeScale.installer_local_pre_upgrade,
                KeyringLargeScale.installer_local_post_upgrade,
                KeyringLargeScale.group_installers,
                KeyringLargeScale.branch_custom,
                KeyringLargeScale.target_env,
                KeyringLargeScale.start_time,
                KeyringLargeScale.version,
                KeyringLargeScale.version_pre_upgrade,
                KeyringLargeScale.version_ha1,
                KeyringLargeScale.version_ha2,
                KeyringLargeScale.version_ha3,
                KeyringLargeScale.version_upgrade_ha1,
                KeyringLargeScale.version_upgrade_ha2,
                KeyringLargeScale.version_upgrade_ha3,
                KeyringLargeScale.build_id,
                KeyringLargeScale.test_id,
                KeyringLargeScale.test_description,
                KeyringLargeScale.branch_ha1,
                KeyringLargeScale.branch_ha2,
                KeyringLargeScale.branch_ha3,
                KeyringLargeScale.branch_upgrade_ha1,
                KeyringLargeScale.branch_upgrade_ha2,
                KeyringLargeScale.branch_upgrade_ha3,
                KeyringLargeScale.docker_network_existed_on_start,
                KeyringLargeScale.influxdb_ip,
                KeyringLargeScale.grafana_hostname,
                KeyringLargeScale.end_time,
                KeyringLargeScale.validation_result,
                KeyringLargeScale.validation_errors,
                KeyringLargeScale.result_to_upload,
                KeyringLargeScale.result,
                ]

        @vault.vaulter(input_keys=keys)
        def _get(**kwargs):
            assert len([k for k in keys if k in kwargs]) == len(keys)
        _get()

    def test_get_threaded(self):
        # Note the use of varvault.VaultFlags.silent() here. It will speed up the processing significantly.
        # It brings processing down from 1.6 seconds to 0.16 seconds for 500 parallel requests.
        vault = varvault.from_vault(KeyringLargeScale, "vault", varvault.JsonFilehandler(large_vault_file), varvault.VaultFlags.silent(), varvault.VaultFlags.remove_existing_log_file(), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        keys = [KeyringLargeScale.workspace_dir,
                KeyringLargeScale.test_time,
                KeyringLargeScale.cpus_per_container,
                KeyringLargeScale.docker_network,
                KeyringLargeScale.branch,
                KeyringLargeScale.descriptor_file,
                KeyringLargeScale.logname,
                KeyringLargeScale.log_out_dir,
                KeyringLargeScale.hostsfile_path,
                KeyringLargeScale.grafana_port,
                KeyringLargeScale.influxdb_database,
                KeyringLargeScale.installer_local_pre_upgrade,
                KeyringLargeScale.installer_local_post_upgrade,
                KeyringLargeScale.group_installers,
                KeyringLargeScale.branch_custom,
                KeyringLargeScale.target_env,
                KeyringLargeScale.start_time,
                KeyringLargeScale.version,
                KeyringLargeScale.version_pre_upgrade,
                KeyringLargeScale.version_ha1,
                KeyringLargeScale.version_ha2,
                KeyringLargeScale.version_ha3,
                KeyringLargeScale.version_upgrade_ha1,
                KeyringLargeScale.version_upgrade_ha2,
                KeyringLargeScale.version_upgrade_ha3,
                KeyringLargeScale.build_id,
                KeyringLargeScale.test_id,
                KeyringLargeScale.test_description,
                KeyringLargeScale.branch_ha1,
                KeyringLargeScale.branch_ha2,
                KeyringLargeScale.branch_ha3,
                KeyringLargeScale.branch_upgrade_ha1,
                KeyringLargeScale.branch_upgrade_ha2,
                KeyringLargeScale.branch_upgrade_ha3,
                KeyringLargeScale.docker_network_existed_on_start,
                KeyringLargeScale.influxdb_ip,
                KeyringLargeScale.grafana_hostname,
                KeyringLargeScale.end_time,
                KeyringLargeScale.validation_result,
                KeyringLargeScale.validation_errors,
                KeyringLargeScale.result_to_upload,
                KeyringLargeScale.result,
                ]

        @vault.vaulter(input_keys=keys)
        async def _get(thread_id, **kwargs):
            assert isinstance(thread_id, int)
            assert len([k for k in keys if k in kwargs]) == len(keys)

        num_threads = 500
        thread_ids = [i for i in range(num_threads)]
        logger.info(f"Number of threads: {len(thread_ids)}")
        start = time.time()
        varvault.concurrent_execution(_get, thread_ids)
        logger.info(f"Time (seconds): {time.time() - start}")

    def test_live_update(self):
        vault = varvault.from_vault(KeyringLargeScale, "vault", varvault.JsonFilehandler(vault_file_new, live_update=True), varvault.VaultFlags.live_update(), varvault.VaultFlags.remove_existing_log_file())

        keys = [KeyringLargeScale.workspace_dir,
                KeyringLargeScale.test_time,
                KeyringLargeScale.cpus_per_container,
                KeyringLargeScale.docker_network,
                KeyringLargeScale.branch,
                KeyringLargeScale.descriptor_file,
                KeyringLargeScale.logname,
                KeyringLargeScale.log_out_dir,
                KeyringLargeScale.hostsfile_path,
                KeyringLargeScale.grafana_port,
                KeyringLargeScale.influxdb_database,
                KeyringLargeScale.installer_local_pre_upgrade,
                KeyringLargeScale.installer_local_post_upgrade,
                KeyringLargeScale.group_installers,
                KeyringLargeScale.branch_custom,
                KeyringLargeScale.target_env,
                KeyringLargeScale.start_time,
                KeyringLargeScale.version,
                KeyringLargeScale.version_pre_upgrade,
                KeyringLargeScale.version_ha1,
                KeyringLargeScale.version_ha2,
                KeyringLargeScale.version_ha3,
                KeyringLargeScale.version_upgrade_ha1,
                KeyringLargeScale.version_upgrade_ha2,
                KeyringLargeScale.version_upgrade_ha3,
                KeyringLargeScale.build_id,
                KeyringLargeScale.test_id,
                KeyringLargeScale.test_description,
                KeyringLargeScale.branch_ha1,
                KeyringLargeScale.branch_ha2,
                KeyringLargeScale.branch_ha3,
                KeyringLargeScale.branch_upgrade_ha1,
                KeyringLargeScale.branch_upgrade_ha2,
                KeyringLargeScale.branch_upgrade_ha3,
                KeyringLargeScale.docker_network_existed_on_start,
                KeyringLargeScale.influxdb_ip,
                KeyringLargeScale.grafana_hostname,
                KeyringLargeScale.end_time,
                KeyringLargeScale.validation_result,
                KeyringLargeScale.validation_errors,
                KeyringLargeScale.result_to_upload,
                KeyringLargeScale.result,
                ]

        # Load the existing vault file and write the contents to the temporary file
        contents = json.load(open(large_vault_file))
        json.dump(contents, open(vault_file_new, "w"), indent=2)

        # Since we use live update, the contents of the existing vault file should now be loaded into the vault.
        @vault.vaulter(input_keys=keys)
        def _get(**kwargs):
            assert len([k for k in keys if k in kwargs]) == len(keys)
        _get()
