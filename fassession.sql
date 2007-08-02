-- python-fedora, python module to interact with Fedora Infrastructure Services
-- Copyright (C) 2007  Red Hat Software Inc
--
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program; if not, write to the Free Software
-- Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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

