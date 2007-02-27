-- fassession.sql Defines the database that we use to tie the account system to
-- sessions (as used by turbogears.)

drop database fassession2;
create database fassession2 with encoding='UTF8';
\c fassession2

create table visit (
  visit_key varchar(40) primary key,
  created timestamp not null default now(),
  expiry timestamp
);

create table visit_identity (
  visit_key varchar(40) primary key,
  user_id text
);

create index visit_identity_user_idx on visit_identity (user_id);

grant all on visit, visit_identity to apache;

