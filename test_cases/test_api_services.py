# -*- coding: utf8 -*-
"""Tests for many API endpoints that do not depend on workspace_name"""

import pytest

from server.api.modules.services import ServiceView
from test_cases import factories
from test_api_workspaced_base import ReadOnlyAPITests
from server.models import (
    Service
)
from test_cases.factories import HostFactory


@pytest.mark.usefixtures('logged_user')
class TestListServiceView(ReadOnlyAPITests):
    model = Service
    factory = factories.ServiceFactory
    api_endpoint = 'services'
    #unique_fields = ['ip']
    #update_fields = ['ip', 'description', 'os']
    view_class = ServiceView

    def test_service_list_backwards_compatibility(self, test_client,
                                                  second_workspace, session):
        self.factory.create(workspace=second_workspace)
        session.commit()
        res = test_client.get(self.url())
        assert res.status_code == 200
        assert 'services' in res.json
        for service in res.json['services']:
            assert set([u'id', u'key', u'value']) == set(service.keys())
            object_properties = [
                u'status',
                u'protocol',
                u'description',
                u'_rev',
                u'owned',
                u'owner',
                u'credentials',
                u'name',
                u'version',
                u'_id',
                u'metadata'
            ]
            expected = set(object_properties)
            result = set(service['value'].keys())
            assert expected <= result

    def test_create_service(self, test_client, host, session):
        session.commit()
        data = {
            "name": "ftp",
            "description": "test. test",
            "owned": False,
            "ports": [21],
            "protocol": "tcp",
            "status": "open",
            "parent": host.id
        }
        res = test_client.post(self.url(), data=data)
        assert res.status_code == 201
        service = Service.query.get(res.json['_id'])
        assert service.name == "ftp"
        assert service.port == 21
        assert service.host is host

    def test_create_fails_with_host_of_other_workspace(self, test_client,
                                                       host, session,
                                                       second_workspace):
        session.commit()
        assert host.workspace_id != second_workspace.id
        data = {
            "name": "ftp",
            "description": "test. test",
            "owned": False,
            "ports": [21],
            "protocol": "tcp",
            "status": "open",
            "parent": host.id
        }
        res = test_client.post(self.url(workspace=second_workspace), data=data)
        assert res.status_code == 400
        assert 'Host with id' in res.data

    def test_update_fails_with_host_of_other_workspace(self, test_client,
                                                       second_workspace,
                                                       host_factory,
                                                       session):
        host = host_factory.create(workspace=second_workspace)
        session.commit()
        assert host.workspace_id != self.first_object.workspace_id
        data = {
            "name": "ftp",
            "description": "test. test",
            "owned": False,
            "ports": [21],
            "protocol": "tcp",
            "status": "open",
            "parent": host.id
        }
        res = test_client.put(self.url(self.first_object), data=data)
        assert res.status_code == 400
        assert 'Can\'t change service parent.' in res.data

    def _raw_put_data(self, id, parent=None, status='open', protocol='tcp', ports=None):
        if not ports:
            ports = [22]
        raw_data = {"status": status,
                    "protocol": protocol,
                    "description": "",
                    "_rev": "",
                    "metadata": {"update_time": 1510945708000, "update_user": "", "update_action": 0, "creator": "",
                                 "create_time": 1510945708000, "update_controller_action": "", "owner": "leonardo",
                                 "command_id": None},
                    "owned": False,
                    "owner": "",
                    "version": "",
                    "_id": id,
                    "ports": ports,
                    "name": "ssh2",
                    "type": "Service"}
        if parent:
            raw_data['parent'] = parent
        return raw_data

    def test_update_with_json_from_webui(self, test_client, session):
        service = self.factory()
        session.commit()
        raw_data = self._raw_put_data(service.id)

        res = test_client.put(self.url(service, workspace=service.workspace), data=raw_data)
        assert res.status_code == 200
        updated_service = Service.query.filter_by(id=service.id).first()
        assert updated_service.status == 'open'
        assert updated_service.name == 'ssh2'

    def test_update_cant_change_parent(self, test_client, session):
        service = self.factory()
        host = HostFactory.create()
        session.commit()
        raw_data = self._raw_put_data(service.id, parent=host.id)
        res = test_client.put(self.url(service, workspace=service.workspace), data=raw_data)
        assert res.status_code == 400
        assert 'Can\'t change service parent.' in res.data
        updated_service = Service.query.filter_by(id=service.id).first()
        assert updated_service.name == service.name

    def test_update_status(self, test_client, session):
        service = self.factory(status='open')
        session.commit()
        raw_data = self._raw_put_data(service.id, parent=service.host.id, status='closed')
        res = test_client.put(self.url(service, workspace=service.workspace), data=raw_data)
        assert res.status_code == 200
        updated_service = Service.query.filter_by(id=service.id).first()
        assert updated_service.status == 'closed'

    def test_update_ports(self, test_client, session):
        service = self.factory(port=22)
        session.commit()
        raw_data = self._raw_put_data(service.id, parent=service.host.id, ports=[221])
        res = test_client.put(self.url(service, workspace=service.workspace), data=raw_data)
        assert res.status_code == 200
        updated_service = Service.query.filter_by(id=service.id).first()
        assert updated_service.port == 221

    def test_update_cant_change_id(self, test_client, session):
        service = self.factory()
        host = HostFactory.create()
        session.commit()
        raw_data = self._raw_put_data(service.id)
        res = test_client.put(self.url(service, workspace=service.workspace), data=raw_data)
        assert res.status_code == 200
        assert res.json['id'] == service.id