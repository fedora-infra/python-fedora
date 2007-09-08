-- python-fedora, python module to interact with Fedora Infrastructure Services
-- Copyright © 2007  Red Hat, Inc. All rights reserved.
--
-- This copyrighted material is made available to anyone wishing to use, modify,
-- copy, or redistribute it subject to the terms and conditions of the GNU
-- General Public License v.2.  This program is distributed in the hope that it
-- will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
-- implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
-- See the GNU General Public License for more details.  You should have
-- received a copy of the GNU General Public License along with this program;
-- if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
-- Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
-- incorporated in the source code or documentation are not subject to the GNU
-- General Public License and may only be used or replicated with the express
-- permission of Red Hat, Inc.
--
-- Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>

-- fassession.sql Defines the database that we use to tie the account system to
-- sessions (as used by turbogears.)

drop database fassession;
create database fassession with encoding='UTF8';
\c fassession

create table visit (
  visit_key varchar(40) primary key,
  created timestamp not null default now(),
  expiry timestamp
);

create table visit_identity (
  visit_key varchar(40) primary key,
  user_id integer
);

create index visit_identity_user_idx on visit_identity (user_id);

grant all on visit, visit_identity to apache;

